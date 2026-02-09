#!/usr/bin/env python3
"""Standalone command bridge for NEXUS hook pipeline.

Runs an arbitrary command and feeds a Claude-compatible PostToolUse event into
quality gate / self-heal / auto-learn hooks so standalone scripts can benefit
from the same safety and learning pipeline.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

CLAUDE_DIR = pathlib.Path.home() / ".claude"
HOOKS_DIR = CLAUDE_DIR / "hooks"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _truncate(value: str, limit: int = 8000) -> str:
    if len(value) <= limit:
        return value
    return value[-limit:]


def _parse_hook_output(text: str) -> Dict[str, Any]:
    content = (text or "").strip()
    if not content:
        return {}
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"raw": _truncate(content)}


def _run_hook(script_path: pathlib.Path, event: Dict[str, Any], cwd: pathlib.Path) -> Dict[str, Any]:
    if not script_path.exists():
        return {
            "ran": False,
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
            "parsed": {"skipped": f"missing_hook:{script_path.name}"},
        }

    proc = subprocess.run(
        ["python3", str(script_path)],
        input=json.dumps(event),
        text=True,
        capture_output=True,
        cwd=str(cwd),
    )
    return {
        "ran": True,
        "exit_code": proc.returncode,
        "stdout": _truncate(proc.stdout),
        "stderr": _truncate(proc.stderr),
        "parsed": _parse_hook_output(proc.stdout),
    }


def _run_fix_process_one(cwd: pathlib.Path) -> Dict[str, Any]:
    cli = CLAUDE_DIR / "nexus_cli.py"
    if not cli.exists():
        return {
            "ran": False,
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
            "parsed": {"skipped": "missing_nexus_cli"},
        }

    proc = subprocess.run(
        ["python3", str(cli), "fix", "process-one"],
        text=True,
        capture_output=True,
        cwd=str(cwd),
    )
    return {
        "ran": True,
        "exit_code": proc.returncode,
        "stdout": _truncate(proc.stdout),
        "stderr": _truncate(proc.stderr),
        "parsed": _parse_hook_output(proc.stdout),
    }


def _build_event(command_str: str, cwd: pathlib.Path, rc: int, stdout: str, stderr: str, duration: float) -> Dict[str, Any]:
    return {
        "tool_name": "Bash",
        "tool_input": {
            "command": command_str,
            "invoker": "nexus_exec",
        },
        "tool_response": {
            "success": rc == 0,
            "exit_code": rc,
            "stdout": _truncate(stdout),
            "stderr": _truncate(stderr),
            "duration_sec": round(duration, 4),
        },
        "cwd": str(cwd),
        "timestamp": _now_iso(),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="nexus_exec",
        description="Run standalone command through NEXUS quality/self-heal pipeline",
    )
    parser.add_argument("--cwd", default=os.getcwd(), help="Working directory for command and hooks")
    parser.add_argument("--shell", action="store_true", help="Execute command through shell")
    parser.add_argument("--skip-quality-gate", action="store_true", help="Skip quality gate hook")
    parser.add_argument("--skip-auto-learn", action="store_true", help="Skip auto-learn hook")
    parser.add_argument("--process-fix-one", action="store_true", help="Run one fix verification after hooks")
    parser.add_argument("--json-only", action="store_true", help="Do not print command output; only final JSON summary")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Command to run (use -- before command)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    command_args = list(args.command)
    if command_args and command_args[0] == "--":
        command_args = command_args[1:]

    if not command_args:
        print(json.dumps({"error": "no command provided"}, ensure_ascii=False))
        return 2

    cwd = pathlib.Path(args.cwd).expanduser().resolve()
    cwd.mkdir(parents=True, exist_ok=True)

    if args.shell:
        command_str = " ".join(command_args)
        command_for_run: Any = command_str
    else:
        command_str = " ".join(shlex.quote(part) for part in command_args)
        command_for_run = command_args

    start = time.time()
    cmd_proc = subprocess.run(
        command_for_run,
        cwd=str(cwd),
        text=True,
        capture_output=True,
        shell=args.shell,
    )
    duration = time.time() - start

    if not args.json_only:
        if cmd_proc.stdout:
            sys.stdout.write(cmd_proc.stdout)
        if cmd_proc.stderr:
            sys.stderr.write(cmd_proc.stderr)

    event = _build_event(
        command_str=command_str,
        cwd=cwd,
        rc=cmd_proc.returncode,
        stdout=cmd_proc.stdout,
        stderr=cmd_proc.stderr,
        duration=duration,
    )

    quality_gate_result = {
        "ran": False,
        "exit_code": 0,
        "parsed": {"skipped": "disabled"},
        "stdout": "",
        "stderr": "",
    }
    if not args.skip_quality_gate:
        quality_gate_result = _run_hook(HOOKS_DIR / "quality_gate.py", event, cwd)

    self_heal_result = {
        "ran": False,
        "exit_code": 0,
        "parsed": {"skipped": "command_success"},
        "stdout": "",
        "stderr": "",
    }
    if cmd_proc.returncode != 0:
        self_heal_result = _run_hook(HOOKS_DIR / "nexus_self_heal.py", event, cwd)

    auto_learn_result = {
        "ran": False,
        "exit_code": 0,
        "parsed": {"skipped": "disabled"},
        "stdout": "",
        "stderr": "",
    }
    if not args.skip_auto_learn:
        auto_learn_result = _run_hook(HOOKS_DIR / "nexus_auto_learn.py", event, cwd)

    fix_process_result = {
        "ran": False,
        "exit_code": 0,
        "parsed": {"skipped": "not_requested"},
        "stdout": "",
        "stderr": "",
    }
    if args.process_fix_one:
        fix_process_result = _run_fix_process_one(cwd)

    overall_exit = cmd_proc.returncode
    if overall_exit == 0 and quality_gate_result.get("exit_code", 0) != 0:
        overall_exit = int(quality_gate_result.get("exit_code", 0))

    summary = {
        "timestamp": _now_iso(),
        "cwd": str(cwd),
        "command": command_str,
        "command_exit_code": cmd_proc.returncode,
        "quality_gate": {
            "ran": quality_gate_result["ran"],
            "exit_code": quality_gate_result["exit_code"],
            "result": quality_gate_result["parsed"],
        },
        "self_heal": {
            "ran": self_heal_result["ran"],
            "exit_code": self_heal_result["exit_code"],
            "result": self_heal_result["parsed"],
        },
        "auto_learn": {
            "ran": auto_learn_result["ran"],
            "exit_code": auto_learn_result["exit_code"],
            "result": auto_learn_result["parsed"],
        },
        "fix_process_one": {
            "ran": fix_process_result["ran"],
            "exit_code": fix_process_result["exit_code"],
            "result": fix_process_result["parsed"],
        },
        "overall_exit_code": overall_exit,
    }

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return int(overall_exit)


if __name__ == "__main__":
    raise SystemExit(main())
