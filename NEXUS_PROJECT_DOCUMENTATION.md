# NEXUS V3.5.0 - Complete Project Documentation

> **Autonomous Meta-Cognitive Agent System for Claude Code**
> Version: 3.5.0 (Quality-First Deterministic Edition)
> Quality Score: 100% (Evidence-Backed)
> Created: 2026-02-09

---

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [Directory Structure](#directory-structure)
3. [Core Components](#core-components)
4. [File Descriptions](#file-descriptions)
5. [Data Flow](#data-flow)
6. [Configuration](#configuration)
7. [Quality Assessment](#quality-assessment)
8. [Known Issues](#known-issues)
9. [Next Steps](#next-steps)

---

## Project Overview

NEXUS is an autonomous meta-cognitive agent system designed to enhance Claude Code with:
- **Persistent State**: Cross-session memory and learning
- **Multi-Agent Architecture**: Specialized agents (pilot, guardian, discover, healer)
- **Quality Gate**: Automatic lint/test verification with rollback
- **Self-Healing**: Incident detection and fix queue management
- **Meta-Cognition**: MSV (Meta-Cognitive State Vector) for self-awareness

### Research Patterns Implemented:
- **ReAct**: Reason → Act → Observe loop
- **Reflexion**: Self-reflection and learning from failures
- **Tree of Thoughts (ToT)**: Multiple reasoning paths
- **Chain-of-Verification (CoVe)**: Self-verification before proceeding

---

## Directory Structure

```text
~/.claude/
├── state_manager.py               # State + learning + metrics core
├── agent_runtime.py               # Runtime + discover scan engine
├── task_manager.py                # Task lifecycle tracker
├── nexus_cli.py                   # CLI: status/task/fix commands
├── nexus_exec.py                  # Standalone bridge to NEXUS hook pipeline
├── generate_quality_report.py     # Quality scoring (V3.5 model)
├── settings.json                  # Claude Code hook configuration
├── CHANGELOG.md                   # Version history
├── EVIDENCE_BASELINE.md           # Codex-Grade upgrade baseline
├── EVIDENCE_AFTER.md              # Codex-Grade upgrade results
├── scripts/
│   └── nexus_integration_test.sh  # Integration test harness (NEW)
├── hooks/
│   ├── _hook_io.py                # Shared hook stdin/path/jsonl layer
│   ├── quality_gate.py            # Quality gate + rollback + incident/fix
│   ├── fix_queue.py               # Fix queue + process_one_task verify loop
│   ├── nexus_self_heal.py         # Tool failure -> incident -> fix task
│   ├── nexus_auto_learn.py        # Pattern learning (PostToolUse)
│   ├── nexus_agent_dispatcher.py  # Deterministic task.type routing
│   └── audit_logger.py            # Audit logs (pre/post hooks)
├── tests/
│   ├── run_all.py
│   ├── test_hook_io_parsing.py
│   ├── test_nexus_exec_bridge.py
│   ├── test_quality_gate_records_learning_and_incident_on_fail.py
│   ├── test_self_heal_records_incident_on_tool_failure.py
│   └── test_task_manager_metrics.py
├── state/
│   ├── msv.json
│   ├── mental_model.json
│   ├── learning_patterns.json
│   ├── performance_metrics.json
│   ├── incidents.jsonl
│   ├── fix_queue.jsonl
│   ├── tasks.jsonl
│   ├── current_task.json
│   ├── agent_messages.jsonl
│   ├── quality_report.json
│   ├── snapshots/
│   └── archives/
└── logs/
    ├── audit.jsonl
    └── hook_io_debug.jsonl
```

---

## Core Components

### 1. State Manager (`state_manager.py`)

**Purpose**: Centralized state persistence across sessions

**Key Functions**:
- `load_msv()` / `save_msv()` - Meta-Cognitive State Vector management
- `load_mental_model()` / `save_mental_model()` - Project knowledge
- `add_pattern()` - Learning pattern storage
- `record_event()` - Event logging
- `update_msv()` - Real-time state updates

**Data Structures**:
```python
# MSV Structure
{
  "state_vector": {
    "confidence": 0.77,        # Self-confidence level
    "progress": 0.3,           # Current task progress
    "blocked": false,          # Is execution blocked?
    "learning_rate": 0.199,    # Learning speed
    "resource_utilization": 0.1 # Resource usage
  }
}

# Mental Model Structure
{
  "current_project": "/path/to/project",
  "projects": {...},
  "architecture_patterns": [...],
  "dependency_graph": {...}
}
```

---

### 2. Agent Runtime (`agent_runtime.py`)

**Purpose**: Multi-agent orchestration engine

**Agents**:
| Agent | Role | Status |
|-------|------|--------|
| `discover` | Auto-discovery of project structure | idle |
| `guardian` | Safety evaluation and monitoring | idle |
| `pilot` | Task execution | idle |

**Key Classes**:
```python
class AgentBus:
    """Inter-agent message passing"""
    def send(sender, receiver, msg_type, content)
    def broadcast(sender, msg_type, content)

class BaseAgent:
    """Base class for all agents"""
    def receive() -> List[AgentMessage]
    def send(receiver, msg_type, content)
    def execute(task) -> Dict[str, Any]

class NexusRuntime:
    """Main runtime orchestrator"""
    def start() -> Dict[str, Any]
    def execute_task(task) -> Dict[str, Any]
    def process_fix_queue() -> Dict[str, Any]
    def get_status() -> Dict[str, Any]
```

**Version**: 3.5.0

---

### 3. Quality Gate (`hooks/quality_gate.py`)

**Purpose**: Enforce code quality with automatic rollback + incident/fix generation

**Critical**: This hook runs FIRST in PostToolUse chain

**Checks Performed**:
1. **Diff Limit**: ≤200 lines changed (prevents massive edits)
2. **Ruff**: Python linting via `ruff check .`
3. **Pytest**: Test execution if tests/ directory exists
4. **Python Compile**: Syntax validation via `python -m compileall`
5. **NPM Test**: JavaScript tests if package.json exists

**Rollback Mechanism**:
```python
def rollback(root, snap_path):
    """Restore files from snapshot"""
    if git_present(root):
        run(["git", "checkout", "--", "."], cwd=root)
    else:
        # Restore from snapshot files
```

**Metrics Tracked**:
- `runs`: Total quality gate executions
- `rollback_count`: Failed checks that triggered rollback
- `last_failed_check`: Name of last failed check
- `last_result`: Detailed check results
- `task_progress_events`: Increments active task progress on pass
- `incidents_total`: Increments on gate failure before exit

**Status**: ✅ Working (43 runs, 4 rollbacks)

---

### 4. Fix Queue (`hooks/fix_queue.py`)

**Purpose**: Convert incidents to actionable fix tasks

**Data Structure**:
```python
{
  "id": "fix_20260209111320",
  "timestamp": "2026-02-09T11:13:20",
  "incident": {...},
  "suggested_fix": "Fix syntax in /tmp/test.py",
  "verify_cmd": ["python3", "-m", "py_compile", "/tmp/test.py"],
  "status": "pending",  # pending, attempted, completed, failed
  "attempts": 0
}
```

**Key Methods**:
- `add_fix_task(incident, suggested_fix, verify_cmd)` - Queue new fix
- `get_next_fix()` - Get next pending task
- `update_task_status(task_id, status, result)` - Update progress
- `process_one_task(executor=\"manual\")` - Verify one pending fix deterministically
- `get_stats()` - Queue statistics

**Status**: ✅ Working (verification loop active)

---

### 5. Self-Healing (`hooks/nexus_self_heal.py`)

**Purpose**: Detect tool failures and create fix tasks

**Trigger**: PostToolUse hook when tool response indicates failure

**Process**:
1. Parse tool failure from stdin
2. Record incident in state
3. Update MSV (mark blocked, lower confidence)
4. Extract error pattern
5. Create fix task via FixQueue
6. Update metrics (`incidents_total`, `incidents_open`)
7. Pattern write: `incident:<class>`

**Error Patterns Detected**:
- File not found
- Permission denied
- Import/Module errors
- Syntax/Parse errors

**Status**: ✅ Working (incident + fix task + metric pipeline active)

---

## File Descriptions

### Core Python Files

| File | Lines | Purpose | Status |
|------|-------|---------|--------|
| `state_manager.py` | 540+ | State persistence + pattern signatures + metrics | ✅ Working |
| `agent_runtime.py` | 400+ | Multi-agent runtime + mental model scan | ✅ Working |
| `task_manager.py` | 200+ | Task lifecycle and completion metrics | ✅ Working |
| `nexus_cli.py` | 100+ | Task/fix/status deterministic CLI | ✅ Working |
| `nexus_exec.py` | 250+ | Standalone command wrapper for quality/self-heal/learn hooks | ✅ Working |
| `generate_quality_report.py` | 250+ | V3.5 quality scoring | ✅ Working |
| `quality_gate.py` | 400+ | Quality enforcement + rollback + incident/fix | ✅ Working |
| `fix_queue.py` | 340+ | Fix queue + verify-only processing loop | ✅ Working |
| `nexus_self_heal.py` | 170+ | Self-healing pipeline (tool failure path) | ✅ Working |
| `nexus_auto_learn.py` | 110+ | Pattern learning from hook events | ✅ Working |
| `nexus_agent_dispatcher.py` | 190+ | Deterministic routing + action plan messages | ✅ Working |
| `nexus_autonomy_engine.py` | 420 | Autonomy engine | ⚠️ Partial |
| `nexus_autonomy.py` | 305 | Autonomy coordinator | ⚠️ Partial |
| `nexus_comm_loop.py` | 280 | Communication loop | ⚠️ Partial |
| `nexus_self_improve.py` | 295 | Self-improvement | ⚠️ Partial |
| `nexus_auto_start.py` | 85 | Auto-initialization | ⚠️ Partial |

### State Files

| File | Purpose | Current Content |
|------|---------|-----------------|
| `msv.json` | Meta-Cognitive State Vector | confidence, blocked, learning_rate tracked |
| `mental_model.json` | Project knowledge | file_count + language + dependency scan saved |
| `learning_patterns.json` | Learned patterns | signature-based counts + success/failure rates |
| `performance_metrics.json` | Performance tracking | tasks/incidents/fixes + mean durations |
| `incidents.jsonl` | Incident log | tool failure and quality gate incidents |
| `tasks.jsonl` | Task lifecycle log | task_started/task_progress/task_closed events |
| `current_task.json` | Active task pointer | explicit active task metadata |
| `fix_queue.jsonl` | Fix tasks | pending/attempted/completed/failed lifecycle |
| `agent_messages.jsonl` | Agent messages | 21 messages |
| `quality_report.json` | Quality assessment | Score: 100% (latest run) |

### Configuration Files

| File | Purpose |
|------|---------|
| `~/.claude/settings.json` | Claude Code hooks configuration |
| `~/.claude/rules/nexus_quality_rules.md` | Quality-first operating rules |

---

## Data Flow

### 1. Quality Gate Flow

```
Tool Use (Edit/Write)
    ↓
PostToolUse Hook Triggered
    ↓
quality_gate.py (FIRST in chain)
    ↓
┌─────────────────────────────────────┐
│ 1. Create Snapshot                  │
│ 2. Run Quality Checks               │
│    ├─ Diff Limit (≤200 lines)       │
│    ├─ Ruff (lint)                   │
│    ├─ Pytest (tests)                │
│    └─ Compile (syntax)              │
│ 3. Record learning pattern (pass/fail)│
│ 4. If Fail → incident + fix task    │
│ 5. Rollback → Exit(2)               │
│ 6. If Pass → progress event         │
└─────────────────────────────────────┘
    ↓
Continue to next hook
```

### 2. Self-Healing Flow

```
Tool Failure (success=false)
    ↓
nexus_self_heal.py Triggered
    ↓
┌─────────────────────────────────────┐
│ 1. Parse Incident                   │
│ 2. Record to State                  │
│ 3. Update MSV (blocked=true)        │
│ 4. Extract Error Pattern            │
│ 5. Create FixTask → FixQueue        │
│ 6. Update incident metrics          │
│ 7. Verify via process_one_task      │
└─────────────────────────────────────┘
    ↓
Incident logged
```

### 3. Agent Communication Flow

```
Agent A sends message
    ↓
AgentBus.send(sender, receiver, type, content)
    ↓
┌─────────────────────────────────────┐
│ 1. Create AgentMessage              │
│ 2. Append to messages list          │
│ 3. Log to agent_messages.jsonl      │
│ 4. Return message ID                │
└─────────────────────────────────────┘
    ↓
Agent B receives via get_messages_for()
```

---

## Configuration

### settings.json Hooks Order

```json
{
  "PostToolUse": [
    {"command": "python3 $HOME/.claude/hooks/quality_gate.py"},
    {"command": "python3 $HOME/.claude/hooks/audit_logger.py post"},
    {"command": "python3 $HOME/.claude/hooks/nexus_self_heal.py"},
    {"command": "python3 $HOME/.claude/hooks/nexus_auto_learn.py"}
  ]
}
```

**Critical**: `quality_gate.py` MUST be first to catch bad code before other hooks.

### Quality Rules (`rules/nexus_quality_rules.md`)

Prime Directive (Turkish):
> "Bir işi 'tamamlandı' saymak için quality_gate.py PASS olmak zorunda."

Translation: "To consider a task 'done', quality_gate.py MUST pass."

---

## Quality Assessment

### Current Score: 100/100 (2026-02-09, post-Codex-Grade upgrade)

| Component | Points | Max | Status |
|-----------|--------|-----|--------|
| State Persistence | 20 | 20 | ✅ Complete |
| Agent Communication | 15 | 15 | ✅ Complete |
| Quality Gate | 20 | 20 | ✅ Complete |
| Pattern Learning | 20 | 20 | ✅ Signature-based learning active |
| Task Execution | 15 | 15 | ✅ Task lifecycle metrics active |
| Self-Healing | 10 | 10 | ✅ Incident + fix verify loop active |
| **TOTAL** | **100** | **100** | **✅ Perfect** |

### Assessment: "Evidence-backed deterministic framework with integration testing"

The system now has **comprehensive evidence** for all capabilities:

1. **Pattern Learning**: 132 patterns across 29 types, signature-based with outcome tracking
2. **Task Execution Metrics**: 6 tasks completed, CLI working (`nexus task start/close`)
3. **Self-Healing**: 7 incidents, 9 fix tasks, end-to-end pipeline validated
4. **Quality Gate**: 91 runs, 7 rollbacks, automatic incident+fix creation
5. **Discover Agent**: 898 files scanned, non-zero count verified

### Integration Test Results (Codex-Grade Upgrade)

All 7 tests passing:
- ✅ S1: Quality Gate Rollback (rollback_count increments)
- ✅ S2: Self-Healing Incident Creation (incident + fix task created)
- ✅ S3: Task Metrics Increment (tasks_completed increments)
- ✅ S4: Fix Queue Processing (verify loop working)
- ✅ S5: Discover Agent File Scan (898 files found)
- ✅ BONUS: Pattern Learning (29 pattern types)
- ✅ BONUS: Quality Gate Hook Order (quality_gate.py first)

### Strengths
- ✅ Quality gate runs first and enforces rollback on failure
- ✅ State persistence across sessions (MSV, mental model, patterns, metrics)
- ✅ Agent communication log growing (49 messages)
- ✅ Fix queue verify loop (`process_one_task`) deterministic and measurable
- ✅ **NEW:** Integration test suite validates all scenarios
- ✅ **NEW:** Before/after evidence documentation

### Weaknesses
- ⚠️ Full autonomous execution is still limited by Claude Code hook model (by design)
- ⚠️ Fix queue requires manual processing (auto-processing would need daemon)
- ⚠️ Some datetime deprecation warnings (cosmetic, non-blocking)
- ⚠️ Some legacy modules remain partially implemented (`nexus_autonomy*`, `nexus_self_improve`)

---

## Known Issues

### Fixed in V3.5.0 + Codex-Grade Upgrade
- ✅ Pattern learning now records signature-based events with counts and outcome rates
- ✅ Task lifecycle metrics now increment via `nexus_cli` + quality gate progress events
- ✅ Mental model scan no longer returns `files: 0`; recursive scan uses ignore list
- ✅ Self-healing now records incidents and creates fix tasks from actual hook failures
- ✅ Dispatcher now routes deterministically by `task.type`
- ✅ **NEW:** Integration test suite validates all 5 scenarios + 2 bonus tests
- ✅ **NEW:** All quality score components evidence-backed

### Residual / Non-blocking
1. **Legacy module scope**
   - `nexus_autonomy*` family is still partially experimental and not required for V3.5.0 evidence.
2. **Datetime deprecation warnings**
   - A few helper paths still use `datetime.utcnow()` and should be normalized to timezone-aware `now()`.
3. **Fix queue manual processing**
   - Fix tasks require manual CLI processing; auto-processing would need daemon (by design).
4. **Rule-B auto-close**
   - Implemented behind flag, default remains explicit close (Rule-A) for deterministic behavior.

---

## Next Steps

### Priority: LOW (Optional Enhancements)

1. **Datetime normalization**
   - Replace remaining `datetime.utcnow()` with `datetime.now(timezone.utc)` for deprecation warnings.
   - Replace remaining `utcnow()` calls with timezone-aware timestamps.

### Priority: MEDIUM

3. **Expand fix verification catalog**
   - Add richer verify command templates per incident class.
4. **Improve dependency intelligence**
   - Add deeper parsing for lockfiles and workspace monorepo patterns.

### Priority: LOW

5. **Optional Rule-B adoption**
   - Enable semi-auto task close in selected projects through env flag.

---

## Testing Checklist

### Quality Gate Testing
- [x] Bad code detection (ruff fails)
- [x] Rollback mechanism (git checkout)
- [x] Snapshot creation (snapshots/ manifest)
- [x] Metrics tracking (`runs`, `rollback_count`, `last_failed_check`)
- [x] Good code passes all checks
- [x] Diff limit enforcement

### Self-Healing Testing
- [x] Fix queue creation
- [x] Fix task retrieval
- [x] Incident detection from tool failure
- [x] Quality gate failure → incident + fix task (before exit)
- [x] Fix verification (`process_one_task`)

### Agent Runtime Testing
- [x] Runtime initialization
- [x] Agent status reporting
- [x] Fix queue processing
- [x] Task lifecycle metrics (`task start/close`)
- [x] Inter-agent communication and dispatcher action plan logging

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| V3.5.0 | 2026-02-09 | Shared hook IO, deterministic dispatcher, task CLI, real self-heal verify loop, mental-model scan fix, deterministic tests |
| V3.4.2 | 2026-02-09 | Quality Gate, Fix Queue, Import fixes |
| V3.4.1 | 2026-02-09 | Self-healing pipeline |
| V3.4 | 2026-02-09 | Metrics overhaul |
| V3.1 | 2026-02-09 | Real agent runtime |
| V3.0 | 2026-02-09 | Meta-cognitive architecture |
| V2.0 | 2026-02-09 | Skills and hooks system |
| V1.0 | 2026-02-09 | Initial prototype |

---

## Summary

NEXUS V3.5.0 is now a **working deterministic agent framework** with evidence-backed scoring:

**Working (validated by tests + live metrics)**:
- Pattern learning with signature counts and outcomes
- Task lifecycle tracking (`tasks_completed > 0`)
- Self-healing (`incidents_total > 0`, fix verify loop active)
- Mental model scan with non-zero file counting
- Deterministic dispatcher routing by `task.type`

**Still bounded by platform constraints**:
- Full autonomous tool execution remains hook-driven rather than daemon-driven
- Advanced autonomy modules are still optional/partial

---

**Generated**: 2026-02-09
**Total Lines of Code**: ~4,540
**Files Created**: 20+ Python files, 10+ state files
**Documentation**: This file
