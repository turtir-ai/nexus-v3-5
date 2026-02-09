# NEXUS V3.5.0

I built this project to make my Claude Code workflow measurable, safe, and recoverable.

I use Claude Code with a z.ai Anthropic-compatible gateway, and this system adds deterministic quality control around tool usage. The core idea is simple: every important action should leave evidence in state files, metrics, and logs.

## What This Project Does

NEXUS adds a quality-first runtime layer on top of Claude Code hooks.

It gives me:
- A strict quality gate with rollback
- Incident recording when tools fail
- A fix queue with deterministic verification commands
- Pattern learning with signature-based counts and outcomes
- Task lifecycle tracking (`start` -> `progress` -> `close`)
- A deterministic dispatcher for agent routing
- A real mental-model scan (no more `files: 0`)

## Current Status (V3.5.0)

This version is implemented and validated.

Latest local quality report (`~/.claude/state/quality_report.json`) shows:
- Pattern Learning: active (`> 0`)
- Task Execution: active (`tasks_completed > 0`)
- Self-Healing: active (`incidents_total > 0`, verify loop executed)
- Quality Gate: `20/20`

## Repository Layout

```text
.
├── README.md
├── NEXUS_PROJECT_DOCUMENTATION.md
├── settings.nexus.sample.json
├── scripts/
│   └── install_to_claude.sh
├── hooks/
│   ├── _hook_io.py
│   ├── quality_gate.py
│   ├── fix_queue.py
│   ├── nexus_self_heal.py
│   ├── nexus_auto_learn.py
│   ├── nexus_agent_dispatcher.py
│   └── audit_logger.py
├── state_manager.py
├── task_manager.py
├── nexus_cli.py
├── nexus_exec.py
├── agent_runtime.py
├── generate_quality_report.py
└── tests/
    ├── run_all.py
    ├── test_utils.py
    ├── test_hook_io_parsing.py
    ├── test_quality_gate_records_learning_and_incident_on_fail.py
    ├── test_self_heal_records_incident_on_tool_failure.py
    └── test_task_manager_metrics.py
```

## How It Works

### 1) Hook IO Layer
All hook scripts use `hooks/_hook_io.py`.

It reads PostToolUse stdin JSON safely and supports contract fields:
- `tool_name`
- `tool_input`
- `tool_response`
- `cwd`

It is backward-compatible with legacy payloads and logs invalid payloads for debugging.

### 2) Quality Gate First
`quality_gate.py` must stay first in `PostToolUse`.

On every run it:
- Executes checks (diff/ruff/pytest/compileall/npm test as applicable)
- Records pass/fail learning pattern
- Updates metrics
- On failure, creates incident + fix task, then rolls back and exits non-zero

### 3) Self-Healing
`nexus_self_heal.py` handles tool failures.

It:
- Classifies incident type
- Writes incident to `incidents.jsonl`
- Adds a fix task to `fix_queue.jsonl`
- Writes pattern `incident:<class>`

### 4) Fix Queue Verify Loop
`fix_queue.py` includes `process_one_task(executor="manual")`.

This does not auto-edit code. It runs `verify_cmd` only, then marks task:
- `completed` if verify command returns `0`
- `failed` otherwise

### 5) Task Lifecycle
`task_manager.py` + `nexus_cli.py` manage lifecycle state:
- `task start "goal"`
- quality gate pass increments progress
- `task close --success|--fail`

Metrics update in `performance_metrics.json`.

### 6) Deterministic Dispatcher
`nexus_agent_dispatcher.py` routes by `task.type`:
- `scan` -> `discover`
- `safety` -> `guardian`
- `fix` / `implement` -> `pilot`

It writes dispatch + action-plan messages to `agent_messages.jsonl`.

### 7) Standalone Bridge (`nexus_exec.py`)
When scripts run outside Claude Code, hooks are not triggered automatically.

`nexus_exec.py` runs a command and then emits a Claude-compatible event into
the NEXUS pipeline (`quality_gate -> self_heal -> auto_learn`).

Example:
```bash
python3 ~/.claude/nexus_exec.py -- python3 my_script.py
```

With optional fix processing:
```bash
python3 ~/.claude/nexus_exec.py --process-fix-one -- python3 -c "import definitely_missing_module"
```

## Fresh Install On a New Computer

These steps are written so I can move to a new machine and get the same system running.

### Step 1: Requirements
I need:
- macOS or Linux
- Python 3.10+
- Git
- Claude Code
- `gh` CLI (optional for GitHub workflows)
- `ruff` and `pytest` recommended for full quality gate behavior

### Step 2: Clone This Repository
```bash
git clone https://github.com/turtir-ai/nexus-v3-5.git
cd nexus-v3-5
```

### Step 3: Install NEXUS Files Into `~/.claude`
```bash
bash scripts/install_to_claude.sh
```

The installer:
- Copies core files, hooks, and tests into `~/.claude`
- Creates backups under `~/.claude/backups/nexus_install_<timestamp>/`
- Copies `settings.nexus.sample.json` to `~/.claude/settings.nexus.sample.json`

### Step 4: Configure z.ai Gateway For Claude Code
Create key helper script:

```bash
mkdir -p ~/bin
cat > ~/bin/zai-key.sh <<'SH'
#!/usr/bin/env bash
# Replace with your real key retrieval logic
printf '%s' "$ZAI_API_KEY"
SH
chmod +x ~/bin/zai-key.sh
```

Set the key in shell profile:

```bash
# zsh example
echo 'export ZAI_API_KEY="YOUR_REAL_KEY"' >> ~/.zshrc
source ~/.zshrc
```

### Step 5: Merge Settings
Merge `~/.claude/settings.nexus.sample.json` into your `~/.claude/settings.json`.

Critical rule:
- In `PostToolUse`, keep `python3 $HOME/.claude/hooks/quality_gate.py` as the first hook.

### Step 6: Restart Claude Code
Restart so hook and env changes are picked up.

## Validation After Install

### 1) Run Deterministic Tests
```bash
python3 ~/.claude/tests/run_all.py
```

Expected:
- `PASS ...` for all 4 tests
- `RESULT: passed=4 failed=0`

### 2) Generate Quality Report
```bash
python3 ~/.claude/generate_quality_report.py
cat ~/.claude/state/quality_report.json
```

### 3) Manual Failure Simulation
```bash
cat <<'JSON' | python3 ~/.claude/hooks/nexus_self_heal.py
{
  "tool_name": "Bash",
  "tool_input": {
    "command": "python3 -c \"import definitely_missing_module\""
  },
  "tool_response": {
    "success": false,
    "exit_code": 1,
    "stderr": "ModuleNotFoundError: No module named \"definitely_missing_module\""
  },
  "cwd": "."
}
JSON
python3 ~/.claude/nexus_cli.py fix stats
python3 ~/.claude/nexus_cli.py fix process-one
```

If working correctly, incidents and fix tasks should increase.

## Daily Usage

Status:
```bash
python3 ~/.claude/nexus_cli.py status
```

Start and close a task:
```bash
python3 ~/.claude/nexus_cli.py task start "Implement X"
python3 ~/.claude/nexus_cli.py task close --success --note "Done"
```

Fix queue operations:
```bash
python3 ~/.claude/nexus_cli.py fix stats
python3 ~/.claude/nexus_cli.py fix process-one
```

Standalone execution with NEXUS protections:
```bash
python3 ~/.claude/nexus_exec.py -- python3 your_standalone_script.py
```

Dispatcher example:
```bash
python3 ~/.claude/hooks/nexus_agent_dispatcher.py dispatch '{"type":"scan","goal":"refresh model"}'
```

## State Files I Care About

- `~/.claude/state/performance_metrics.json`
- `~/.claude/state/learning_patterns.json`
- `~/.claude/state/incidents.jsonl`
- `~/.claude/state/fix_queue.jsonl`
- `~/.claude/state/tasks.jsonl`
- `~/.claude/state/current_task.json`
- `~/.claude/state/mental_model.json`
- `~/.claude/state/quality_report.json`

## Troubleshooting

### Quality gate exits with non-zero
This is expected when checks fail. Inspect:
- `~/.claude/state/performance_metrics.json`
- `~/.claude/state/incidents.jsonl`
- `~/.claude/state/fix_queue.jsonl`

### No hook effect in Claude Code
Check:
- `~/.claude/settings.json` hook paths
- `quality_gate.py` is first in PostToolUse
- scripts are executable (`chmod +x ~/.claude/hooks/*.py`)

### Missing `ruff` or `pytest`
Install them if you want full checks:
```bash
python3 -m pip install ruff pytest
```

## Design Constraints

This project intentionally avoids heavy dependencies and background daemons.

Everything is built around deterministic hook-driven behavior, because that is the most reliable model for Claude Code environments.

## Author Voice

I built this to make my AI coding workflow honest and testable.

If something is "working", I want proof in logs, metrics, and reproducible tests, not assumptions.
