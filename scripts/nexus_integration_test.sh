#!/usr/bin/env bash
# NEXUS V3.5.0 - Integration Test Harness
# Tests core scenarios plus standalone bridge coverage
#
# Usage: ./scripts/nexus_integration_test.sh [--scenario N] [--verbose]
#
# Exit codes:
# 0 = All tests passed
# 1 = One or more tests failed
# 2 = Prerequisites not met

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Paths
STATE_DIR="$HOME/.claude/state"
HOOKS_DIR="$HOME/.claude/hooks"
NEXUS_CLI="$HOME/.claude/nexus_cli.py"
TEST_TMP_DIR=$(mktemp -d)
export TEST_TMP_DIR

# Cleanup trap
cleanup() {
    rm -rf "$TEST_TMP_DIR"
}
trap cleanup EXIT

# Logging
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[PASS]${NC} $1"; }
log_error() { echo -e "${RED}[FAIL]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

# Test result tracking
test_start() {
    TESTS_RUN=$((TESTS_RUN + 1))
    log_info "Test $TESTS_RUN: $1"
}

test_pass() {
    TESTS_PASSED=$((TESTS_PASSED + 1))
    log_success "$1"
}

test_fail() {
    TESTS_FAILED=$((TESTS_FAILED + 1))
    log_error "$1"
}

# Prerequisites check
check_prerequisites() {
    log_info "Checking prerequisites..."

    local missing=0

    # Check Python 3
    if ! command -v python3 &> /dev/null; then
        log_error "python3 not found"
        missing=1
    fi

    # Check ruff
    if ! command -v ruff &> /dev/null; then
        log_error "ruff not found (install: python3 -m pip install ruff)"
        missing=1
    fi

    # Check NEXUS files
    if [[ ! -f "$NEXUS_CLI" ]]; then
        log_error "nexus_cli.py not found at $NEXUS_CLI"
        missing=1
    fi

    if [[ ! -d "$STATE_DIR" ]]; then
        log_error "State directory not found at $STATE_DIR"
        missing=1
    fi

    if [[ ! -f "$HOME/.claude/settings.json" ]]; then
        log_error "settings.json not found at $HOME/.claude/settings.json"
        missing=1
    fi

    # Check hook order (quality_gate should be first in PostToolUse)
    if [[ -f "$HOME/.claude/settings.json" ]]; then
        local first_ok
        first_ok=$(python3 - <<'PY'
import json, pathlib
settings_path = pathlib.Path.home() / ".claude" / "settings.json"
try:
    data = json.loads(settings_path.read_text())
except Exception:
    print("0")
    raise SystemExit(0)

post_tool_use = data.get("hooks", {}).get("PostToolUse", [])

def first_command(block):
    hooks = block.get("hooks", [])
    for hook in hooks:
        if hook.get("type") == "command" and hook.get("command"):
            return hook["command"]
    return ""

is_valid = False
for block in post_tool_use:
    matcher = str(block.get("matcher", "*"))
    if matcher in ("*", ".*"):
        cmd = first_command(block)
        if "quality_gate.py" in cmd:
            is_valid = True
            break

print("1" if is_valid else "0")
PY
)
        if [[ "$first_ok" != "1" ]]; then
            log_error "quality_gate.py is not the FIRST command in a PostToolUse '*' hook block"
            missing=1
        fi
    fi

    if [[ $missing -eq 1 ]]; then
        return 1
    fi

    log_success "All prerequisites met"
    return 0
}

# Helper: Get JSON value
get_json() {
    local file="$1"
    local key="$2"
    python3 -c "import json; print(json.load(open('$file'))$key)" 2>/dev/null || echo "null"
}

# Helper: Count JSONL lines
count_jsonl() {
    local file="$1"
    if [[ -f "$file" ]]; then
        wc -l < "$file" | tr -d ' '
    else
        echo "0"
    fi
}

ensure_no_active_task() {
    if [[ -f "$STATE_DIR/current_task.json" ]]; then
        python3 "$NEXUS_CLI" task close --fail --note "integration pre-cleanup" > /dev/null 2>&1 || true
    fi
}

# Scenario 1: Quality Gate Rollback
scenario_s1_quality_gate_rollback() {
    test_start "S1: Quality Gate Rollback"

    local test_repo="$TEST_TMP_DIR/s1_repo"

    # Create test repo
    mkdir -p "$test_repo"
    cd "$test_repo"
    git init -q
    git config user.email "test@nexus.local"
    git config user.name "NEXUS Test"

    # Create bad Python file (ruff will fail)
    cat > "$test_repo/test.py" << 'EOF'
def bad_function( ):
    # Unused import
    import os
    import sys
    # Too many blank lines


    pass
EOF

    # Add to git (baseline)
    git add test.py
    git commit -m "Initial commit" -q

    # Now make a bad change
    cat > "$test_repo/test.py" << 'EOF'
def bad_function( ):
    # This will trigger ruff F401 (unused import)
    import definitely_unused_module_xyz
    pass
EOF

    # Get initial rollback count
    local initial_rollback=$(get_json "$STATE_DIR/performance_metrics.json" '["rollback_count"]')

    # Create hook event JSON (stdin input)
    local hook_event="{
        \"tool_name\": \"Write\",
        \"tool_input\": {\"file_path\": \"$test_repo/test.py\"},
        \"tool_response\": {\"success\": true},
        \"cwd\": \"$test_repo\"
    }"

    # Run quality gate with proper stdin input
    cd "$test_repo"
    local gate_output
    local gate_rc
    set +e
    gate_output=$(echo "$hook_event" | python3 "$HOOKS_DIR/quality_gate.py" 2>&1)
    gate_rc=$?
    set -e

    # Check rollback was triggered
    local final_rollback=$(get_json "$STATE_DIR/performance_metrics.json" '["rollback_count"]')

    if [[ "$gate_rc" -eq 2 ]] && [[ "$final_rollback" -gt "$initial_rollback" ]] && echo "$gate_output" | grep -q '"rolled_back": true'; then
        test_pass "Quality gate rollback triggered (rollback_count: $initial_rollback → $final_rollback, exit_code=$gate_rc)"
        return 0
    else
        test_fail "Quality gate rollback validation failed (exit_code=$gate_rc, rollback_count: $initial_rollback → $final_rollback)"
        return 1
    fi
}

# Scenario 2: Self-Healing Incident Creation
scenario_s2_self_healing_incident() {
    test_start "S2: Self-Healing Incident Creation"

    local initial_incidents=$(count_jsonl "$STATE_DIR/incidents.jsonl")
    local initial_fix_tasks=$(count_jsonl "$STATE_DIR/fix_queue.jsonl")

    # Create hook event for tool failure (simulating a Bash command that failed)
    local hook_event="{
        \"tool_name\": \"Bash\",
        \"tool_input\": {\"command\": \"python3 -c 'import definitely_missing_module_xyz_test'\"},
        \"tool_response\": {\"success\": false, \"exit_code\": 1, \"stderr\": \"ModuleNotFoundError: No module named 'definitely_missing_module_xyz_test'\"},
        \"cwd\": \"$TEST_TMP_DIR\"
    }"

    # Run self-heal hook with proper stdin input
    local self_heal_output
    local self_heal_rc
    set +e
    self_heal_output=$(echo "$hook_event" | python3 "$HOOKS_DIR/nexus_self_heal.py" 2>&1)
    self_heal_rc=$?
    set -e

    # Check if incident was recorded
    local final_incidents=$(count_jsonl "$STATE_DIR/incidents.jsonl")
    local final_fix_tasks=$(count_jsonl "$STATE_DIR/fix_queue.jsonl")

    if [[ "$self_heal_rc" -eq 0 ]] && [[ "$final_incidents" -gt "$initial_incidents" ]] && [[ "$final_fix_tasks" -gt "$initial_fix_tasks" ]] && echo "$self_heal_output" | grep -q '"incident_class": "import_error"'; then
        test_pass "Incident and fix task created (incidents: $initial_incidents → $final_incidents, fix_tasks: $initial_fix_tasks → $final_fix_tasks)"
        return 0
    else
        test_fail "Self-healing validation failed (exit_code=$self_heal_rc, incidents: $initial_incidents → $final_incidents, fix_tasks: $initial_fix_tasks → $final_fix_tasks)"
        return 1
    fi
}

# Scenario 3: Task Metrics Increment
scenario_s3_task_metrics() {
    test_start "S3: Task Metrics Increment"

    local initial_completed
    initial_completed=$(get_json "$STATE_DIR/performance_metrics.json" '["tasks_completed"]')

    ensure_no_active_task

    # Start a task
    if ! python3 "$NEXUS_CLI" task start "integration-test-task-$(date +%s)" > /dev/null 2>&1; then
        test_fail "Task start command failed"
        return 1
    fi

    # Small delay to ensure task is recorded
    sleep 0.2

    # Close the task (using correct CLI syntax)
    if ! python3 "$NEXUS_CLI" task close --success --note "integration test" > /dev/null 2>&1; then
        test_fail "Task close command failed"
        return 1
    fi

    # Delay to ensure metrics are flushed
    sleep 0.2

    # Check if tasks_completed incremented
    local final_completed=$(get_json "$STATE_DIR/performance_metrics.json" '["tasks_completed"]')

    if [[ "$final_completed" -gt "$initial_completed" ]]; then
        test_pass "Task metrics incremented (tasks_completed: $initial_completed → $final_completed)"
        return 0
    else
        test_fail "Task metrics did not increment (stayed at $final_completed)"
        return 1
    fi
}

# Scenario 4: Fix Queue Processing
scenario_s4_fix_queue_processing() {
    test_start "S4: Fix Queue Processing"

    local initial_completed initial_failed initial_pending
    initial_completed=$(get_json "$STATE_DIR/performance_metrics.json" '["fixes_completed"]')
    initial_failed=$(get_json "$STATE_DIR/performance_metrics.json" '["fixes_failed"]')
    initial_pending=$(python3 - <<PY
import json, subprocess
out = subprocess.check_output(["python3", "$NEXUS_CLI", "fix", "stats"], text=True)
data = json.loads(out)
print(data.get("pending", 0))
PY
)

    # Process one fix task (if any pending)
    local process_output process_rc
    set +e
    process_output=$(python3 "$NEXUS_CLI" fix process-one 2>&1)
    process_rc=$?
    set -e

    local final_completed final_failed final_pending status
    final_completed=$(get_json "$STATE_DIR/performance_metrics.json" '["fixes_completed"]')
    final_failed=$(get_json "$STATE_DIR/performance_metrics.json" '["fixes_failed"]')
    final_pending=$(python3 - <<PY
import json, subprocess
out = subprocess.check_output(["python3", "$NEXUS_CLI", "fix", "stats"], text=True)
data = json.loads(out)
print(data.get("pending", 0))
PY
)
    status=$(python3 -c 'import json,sys; raw=sys.stdin.read().strip(); print(json.loads(raw).get("status","") if raw else "")' <<<"$process_output" 2>/dev/null || true)

    if [[ "$initial_pending" -gt 0 ]]; then
        if [[ "$process_rc" -eq 0 ]] && [[ "$status" != "no_pending_task" ]] && { [[ "$final_completed" -gt "$initial_completed" ]] || [[ "$final_failed" -gt "$initial_failed" ]] || [[ "$final_pending" -lt "$initial_pending" ]]; }; then
            test_pass "Fix queue processed one task (pending: $initial_pending → $final_pending)"
            return 0
        fi
        test_fail "Fix queue did not process pending task (status=$status, pending: $initial_pending → $final_pending)"
        return 1
    fi

    if [[ "$process_rc" -eq 0 ]] && [[ "$status" == "no_pending_task" ]]; then
        test_pass "Fix queue reports no pending task as expected"
        return 0
    fi

    test_fail "Fix queue response invalid when no pending task (status=$status)"
    return 1
}

# Scenario 5: Discover Agent File Scan
scenario_s5_discover_file_scan() {
    test_start "S5: Discover Agent File Scan"

    # Run agent runtime to trigger discover scan
    local output
    output=$(cd ~/.claude && python3 agent_runtime.py 2>&1 || true)

    # Check if discover returns non-zero file count
    local file_count
    file_count=$(python3 -c 'import re,sys; text=sys.stdin.read(); m=[int(x) for x in re.findall(r"\"file_count\"\s*:\s*(\d+)", text)]; print(max(m) if m else 0)' <<<"$output")

    if [[ -n "$file_count" ]] && [[ "$file_count" -gt 0 ]]; then
        test_pass "Discover agent returns file count > 0 (found $file_count files)"
        return 0
    else
        test_fail "Discover agent returned 0 files or failed (output: $(echo "$output" | head -5))"
        return 1
    fi
}

# Scenario 6: Standalone bridge through nexus_exec.py
scenario_s6_standalone_bridge() {
    test_start "S6: Standalone Bridge (nexus_exec.py)"

    local nexus_exec="$HOME/.claude/nexus_exec.py"
    if [[ ! -f "$nexus_exec" ]]; then
        test_fail "nexus_exec.py not found at $nexus_exec"
        return 1
    fi

    local initial_incidents initial_fix_tasks
    initial_incidents=$(count_jsonl "$STATE_DIR/incidents.jsonl")
    initial_fix_tasks=$(count_jsonl "$STATE_DIR/fix_queue.jsonl")

    local standalone_file="$TEST_TMP_DIR/standalone_bad.py"
    cat > "$standalone_file" <<'EOF'
import treadling

print(user_status)
EOF

    local bridge_output bridge_rc
    set +e
    bridge_output=$(python3 "$nexus_exec" --cwd "$TEST_TMP_DIR" -- python3 "$standalone_file" 2>&1)
    bridge_rc=$?
    set -e

    local final_incidents final_fix_tasks
    final_incidents=$(count_jsonl "$STATE_DIR/incidents.jsonl")
    final_fix_tasks=$(count_jsonl "$STATE_DIR/fix_queue.jsonl")

    local preflight_passed
    preflight_passed=$(python3 -c 'import json,re,sys; raw=sys.stdin.read(); m=re.search(r"(\{[\s\S]*\})\s*$", raw); data=json.loads(m.group(1)) if m else {}; print("1" if (data.get("preflight",{}).get("passed") is False) else "0")' <<<"$bridge_output" 2>/dev/null || echo "0")
    local command_rc
    command_rc=$(python3 -c 'import json,re,sys; raw=sys.stdin.read(); m=re.search(r"(\{[\s\S]*\})\s*$", raw); data=json.loads(m.group(1)) if m else {}; print(data.get("command_exit_code",-1))' <<<"$bridge_output" 2>/dev/null || echo "-1")

    if [[ "$bridge_rc" -ne 0 ]] && [[ "$command_rc" -eq 97 ]] && [[ "$preflight_passed" == "1" ]] && [[ "$final_incidents" -gt "$initial_incidents" ]] && [[ "$final_fix_tasks" -gt "$initial_fix_tasks" ]] && echo "$bridge_output" | grep -q '"self_heal"'; then
        test_pass "Standalone bridge triggers NEXUS pipeline (incidents: $initial_incidents → $final_incidents, fix_tasks: $initial_fix_tasks → $final_fix_tasks)"
        return 0
    fi

    test_fail "Standalone bridge did not trigger expected preflight/pipeline behavior"
    return 1
}

# Bonus: Pattern Learning Verification
bonus_pattern_learning() {
    test_start "BONUS: Pattern Learning Verification"

    # Check if learning_patterns.json has patterns
    local pattern_count
    pattern_count=$(python3 -c "import json; d=json.load(open('$STATE_DIR/learning_patterns.json')); print(len(d.get('patterns', {})))" 2>/dev/null || echo "0")

    if [[ "$pattern_count" -gt 0 ]]; then
        test_pass "Pattern learning active ($pattern_count pattern types found)"
        return 0
    else
        test_fail "No patterns learned"
        return 1
    fi
}

# Bonus: Quality Gate Order Verification
bonus_hook_order() {
    test_start "BONUS: Quality Gate Hook Order"

    local first_ok
    first_ok=$(python3 - <<'PY'
import json, pathlib
settings_path = pathlib.Path.home() / ".claude" / "settings.json"
try:
    data = json.loads(settings_path.read_text())
except Exception:
    print("0")
    raise SystemExit(0)

post_tool_use = data.get("hooks", {}).get("PostToolUse", [])

def first_command(block):
    hooks = block.get("hooks", [])
    for hook in hooks:
        if hook.get("type") == "command" and hook.get("command"):
            return hook["command"]
    return ""

for block in post_tool_use:
    matcher = str(block.get("matcher", "*"))
    if matcher in ("*", ".*"):
        cmd = first_command(block)
        print("1" if "quality_gate.py" in cmd else "0")
        raise SystemExit(0)

print("0")
PY
)

    if [[ "$first_ok" == "1" ]]; then
        test_pass "Quality gate is first in PostToolUse chain"
        return 0
    else
        test_fail "Quality gate is not first in PostToolUse hooks"
        return 1
    fi
}

# Main test runner
main() {
    local run_scenario=""
    local verbose=false

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --scenario|-s)
                run_scenario="$2"
                shift 2
                ;;
            --verbose|-v)
                verbose=true
                shift
                ;;
            --help|-h)
                echo "Usage: $0 [--scenario N] [--verbose]"
                echo ""
                echo "Scenarios:"
                echo "  S1 - Quality Gate Rollback"
                echo "  S2 - Self-Healing Incident Creation"
                echo "  S3 - Task Metrics Increment"
                echo "  S4 - Fix Queue Processing"
                echo "  S5 - Discover Agent File Scan"
                echo "  S6 - Standalone Bridge"
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    echo "=========================================="
    echo "  NEXUS V3.5.0 Integration Test Harness"
    echo "=========================================="
    echo ""

    # Check prerequisites
    if ! check_prerequisites; then
        echo ""
        log_error "Prerequisites not met. Exiting."
        exit 2
    fi

    echo ""

    # Run tests
    if [[ -z "$run_scenario" ]] || [[ "$run_scenario" == "S1" ]]; then
        scenario_s1_quality_gate_rollback
    fi

    if [[ -z "$run_scenario" ]] || [[ "$run_scenario" == "S2" ]]; then
        scenario_s2_self_healing_incident
    fi

    if [[ -z "$run_scenario" ]] || [[ "$run_scenario" == "S3" ]]; then
        scenario_s3_task_metrics
    fi

    if [[ -z "$run_scenario" ]] || [[ "$run_scenario" == "S4" ]]; then
        scenario_s4_fix_queue_processing
    fi

    if [[ -z "$run_scenario" ]] || [[ "$run_scenario" == "S5" ]]; then
        scenario_s5_discover_file_scan
    fi

    if [[ -z "$run_scenario" ]] || [[ "$run_scenario" == "S6" ]]; then
        scenario_s6_standalone_bridge
    fi

    # Bonus tests
    bonus_pattern_learning
    bonus_hook_order

    # Summary
    echo ""
    echo "=========================================="
    echo "  Test Summary"
    echo "=========================================="
    echo "Tests Run:    $TESTS_RUN"
    log_success "Tests Passed: $TESTS_PASSED"
    if [[ $TESTS_FAILED -gt 0 ]]; then
        log_error "Tests Failed: $TESTS_FAILED"
    else
        echo "Tests Failed: $TESTS_FAILED"
    fi
    echo ""

    if [[ $TESTS_FAILED -eq 0 ]]; then
        log_success "ALL TESTS PASSED"
        echo ""
        return 0
    else
        log_error "SOME TESTS FAILED"
        echo ""
        return 1
    fi
}

# Run main
main "$@"
