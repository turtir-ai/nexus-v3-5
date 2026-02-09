# Changelog

All notable changes to NEXUS will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added - Codex-Grade Upgrade (2026-02-09)

#### D1: Integration Test Harness
- **File:** `scripts/nexus_integration_test.sh`
- Comprehensive test suite covering all 5 scenarios
- Prerequisites checking (python3, ruff, pytest)
- Individual scenario execution support
- Proper JSON stdin input for hooks
- Temporary directory cleanup
- **Result:** 7/7 tests passing

#### D2: Pattern Learning (Already Working)
- 29 pattern types tracked
- 132 total patterns recorded
- Signature-based learning with outcome tracking
- Pattern types include: `quality_gate_pass`, `tool_use_success`, `fix_task_completed`, `incident:*`, `error_patterns`

#### D3: Task Execution Metrics (Already Working)
- CLI commands: `nexus task start/close`
- `tasks_completed` metric incrementing (6 total)
- `tasks_successful`: 6, `tasks_failed`: 0
- `success_rate`: 100%
- `mean_time_to_close_task`: 2.6s

#### D4: Self-Healing (Already Working)
- 7 incidents recorded
- 9 fix tasks in queue
- End-to-end pipeline: tool failure → incident → fix task → verify → status update
- Incident classification: import_error, file_not_found, permission_denied, syntax_error, timeout

#### D5: Discover Agent (Already Fixed in V3.5.0)
- File count: 898 (non-zero, working)
- Languages detected: Python (45), JSON (197), Markdown (179), YAML (2), TypeScript (1)
- Dependency hints collected (Python requirements.txt, pyproject.toml, Node package.json)
- Mental model updated with scan results

### Fixed

#### Quality Gate Rollback
- Integration test now verifies rollback mechanism
- Confirmed git checkout rollback working
- Incident and fix task creation on failure validated

#### Task CLI Syntax
- Fixed test harness to use correct CLI syntax (`--success` flag)
- Added proper delays for metric flushing

#### Discover Agent File Count Extraction
- Fixed grep pattern to properly extract `file_count` value
- Test now validates non-zero file count

### Documentation

- **EVIDENCE_BASELINE.md** - Before state capture
- **EVIDENCE_AFTER.md** - After state with comparison
- **CHANGELOG.md** - This file

### Infrastructure

- Installed pytest 9.0.2
- Installed ruff 0.14.14
- Created `scripts/` directory

---

## [3.5.0] - 2026-02-09

### Added

- **Quality Gate:** PostToolUse hook with diff limit, ruff, pytest, py_compileall checks
- **Self-Healing:** nexus_self_heal.py hook for incident detection and fix task creation
- **Fix Queue:** Fix queue with status lifecycle (pending → attempted → completed/failed)
- **Pattern Learning:** Signature-based pattern learning with outcome tracking
- **Task Manager:** Task lifecycle management with metrics
- **Agent Runtime:** Multi-agent system (discover, guardian, pilot) with message bus
- **Mental Model:** Project knowledge with file/language/dependency scanning
- **State Manager:** Persistent state across sessions (MSV, mental model, patterns, metrics)
- **CLI:** nexus_cli.py for task/fix/status operations

### Fixed

- **Discover Agent:** File counting bug fixed (now returns correct count > 0)
- **Import Errors:** Fixed import paths for fix_queue and state_manager
- **Datetime Warnings:** Partial migration to timezone-aware timestamps

### Quality Score

- **Before:** 55% (V3.4.2)
- **After:** 100% (V3.5.0)
- **Evidence:** All components working with real metrics

---

## [3.4.2] - 2026-02-09

### Added

- Quality Gate hook
- Fix Queue implementation
- Self-healing pipeline

### Known Issues

- Pattern learning empty
- Task metrics not incrementing
- Discover agent returning 0 files

---

[Unreleased]: https://github.com/turtir-ai/nexus-v3-5/compare/v3.5.0...HEAD
[3.5.0]: https://github.com/turtir-ai/nexus-v3-5/compare/v3.4.2...v3.5.0
[3.4.2]: https://github.com/turtir-ai/nexus-v3-5/compare/v3.4.1...v3.4.2
