#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLAUDE_DIR="${CLAUDE_DIR:-$HOME/.claude}"
BACKUP_ROOT="$CLAUDE_DIR/backups"
TIMESTAMP="$(date '+%Y%m%d_%H%M%S')"
BACKUP_DIR="$BACKUP_ROOT/nexus_install_$TIMESTAMP"

CORE_FILES=(
  "state_manager.py"
  "task_manager.py"
  "nexus_cli.py"
  "nexus_exec.py"
  "agent_runtime.py"
  "generate_quality_report.py"
)

HOOK_FILES=(
  "_hook_io.py"
  "quality_gate.py"
  "fix_queue.py"
  "nexus_self_heal.py"
  "nexus_auto_learn.py"
  "nexus_agent_dispatcher.py"
  "audit_logger.py"
)

TEST_FILES=(
  "run_all.py"
  "test_utils.py"
  "test_hook_io_parsing.py"
  "test_nexus_exec_bridge.py"
  "test_quality_gate_records_learning_and_incident_on_fail.py"
  "test_self_heal_records_incident_on_tool_failure.py"
  "test_task_manager_metrics.py"
)

mkdir -p "$CLAUDE_DIR" "$CLAUDE_DIR/hooks" "$CLAUDE_DIR/tests" "$CLAUDE_DIR/state" "$CLAUDE_DIR/logs"
mkdir -p "$BACKUP_DIR"

backup_if_exists() {
  local target="$1"
  if [[ -f "$target" ]]; then
    mkdir -p "$BACKUP_DIR/$(dirname "${target#$CLAUDE_DIR/}")"
    cp -f "$target" "$BACKUP_DIR/${target#$CLAUDE_DIR/}"
  fi
}

copy_core() {
  local file
  for file in "${CORE_FILES[@]}"; do
    backup_if_exists "$CLAUDE_DIR/$file"
    cp -f "$REPO_ROOT/$file" "$CLAUDE_DIR/$file"
  done
}

copy_hooks() {
  local file
  for file in "${HOOK_FILES[@]}"; do
    backup_if_exists "$CLAUDE_DIR/hooks/$file"
    cp -f "$REPO_ROOT/hooks/$file" "$CLAUDE_DIR/hooks/$file"
    chmod +x "$CLAUDE_DIR/hooks/$file"
  done
}

copy_tests() {
  local file
  for file in "${TEST_FILES[@]}"; do
    backup_if_exists "$CLAUDE_DIR/tests/$file"
    cp -f "$REPO_ROOT/tests/$file" "$CLAUDE_DIR/tests/$file"
    chmod +x "$CLAUDE_DIR/tests/$file"
  done
}

copy_core
copy_hooks
copy_tests

cp -f "$REPO_ROOT/settings.nexus.sample.json" "$CLAUDE_DIR/settings.nexus.sample.json"

chmod +x "$CLAUDE_DIR/nexus_cli.py" "$CLAUDE_DIR/nexus_exec.py"

cat <<EOF
Install complete.

CLAUDE_DIR: $CLAUDE_DIR
Backup dir : $BACKUP_DIR

Next steps:
1) Merge hooks/env from: $CLAUDE_DIR/settings.nexus.sample.json into your $CLAUDE_DIR/settings.json
2) Ensure PostToolUse order keeps quality_gate first.
3) Run tests:
   python3 $CLAUDE_DIR/tests/run_all.py
EOF
