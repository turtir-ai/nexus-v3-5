#!/usr/bin/env python3
"""Standalone command bridge for NEXUS hook pipeline.

Runs an arbitrary command and feeds a Claude-compatible PostToolUse event into
quality_gate / self_heal / auto_learn hooks so standalone scripts can benefit
from the same safety and learning pipeline.
"""
from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import os
import pathlib
import shlex
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

CLAUDE_DIR = pathlib.Path.home() / ".claude"
HOOKS_DIR = CLAUDE_DIR / "hooks"
_STDLIB_MODULES = set(getattr(sys, "stdlib_module_names", set()))


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


def _build_event(command_str: str, cwd: pathlib.Path, rc: int, stdout: str, stderr: str, duration: float, preflight: Dict[str, Any]) -> Dict[str, Any]:
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
            "preflight": preflight,
        },
        "cwd": str(cwd),
        "timestamp": _now_iso(),
    }


def _is_python_executable(executable: str) -> bool:
    name = pathlib.Path(executable).name.lower()
    return name.startswith("python")


def _extract_python_target(command_args: List[str], cwd: pathlib.Path) -> Optional[Dict[str, str]]:
    if not command_args:
        return None
    if not _is_python_executable(command_args[0]):
        return None

    idx = 1
    while idx < len(command_args):
        token = command_args[idx]

        if token == "-c" and idx + 1 < len(command_args):
            return {"kind": "inline", "value": command_args[idx + 1]}

        if token == "-m" and idx + 1 < len(command_args):
            return {"kind": "module", "value": command_args[idx + 1]}

        if token.startswith("-"):
            idx += 1
            continue

        candidate = pathlib.Path(token)
        if not candidate.is_absolute():
            candidate = (cwd / candidate).resolve()
        return {"kind": "file", "value": str(candidate)}

    return None


def _module_available(module_name: str, cwd: pathlib.Path) -> bool:
    root_name = module_name.split(".")[0]
    if root_name in _STDLIB_MODULES:
        return True

    old_sys_path = list(sys.path)
    try:
        if str(cwd) not in sys.path:
            sys.path.insert(0, str(cwd))
        return importlib.util.find_spec(root_name) is not None
    except Exception:
        return False
    finally:
        sys.path[:] = old_sys_path


def _collect_imports_from_source(source: str) -> List[str]:
    tree = ast.parse(source)
    modules = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                continue
            if node.module:
                modules.add(node.module)

    return sorted(modules)


def _run_preflight_for_source(source: str, cwd: pathlib.Path, source_path: Optional[pathlib.Path]) -> List[Dict[str, Any]]:
    checks: List[Dict[str, Any]] = []

    try:
        ast.parse(source)
        checks.append({"name": "ast_parse", "ok": True, "detail": "syntax parse ok"})
    except SyntaxError as exc:
        checks.append({"name": "ast_parse", "ok": False, "detail": f"SyntaxError: {exc}"})
        return checks

    imports = _collect_imports_from_source(source)
    missing_imports = [mod for mod in imports if not _module_available(mod, cwd)]
    checks.append(
        {
            "name": "import_smoke",
            "ok": len(missing_imports) == 0,
            "detail": "all imports resolvable" if not missing_imports else f"missing imports: {', '.join(missing_imports)}",
            "missing": missing_imports,
        }
    )

    if source_path is not None:
        py_compile_proc = subprocess.run(
            ["python3", "-m", "py_compile", str(source_path)],
            text=True,
            capture_output=True,
        )
        checks.append(
            {
                "name": "py_compile",
                "ok": py_compile_proc.returncode == 0,
                "detail": (py_compile_proc.stderr or py_compile_proc.stdout or "ok").strip()[:1000],
            }
        )

    if shutil_which("ruff") is not None:
        if source_path is None:
            with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as handle:
                handle.write(source)
                tmp_path = pathlib.Path(handle.name)
            try:
                ruff_proc = subprocess.run(
                    ["ruff", "check", str(tmp_path)],
                    text=True,
                    capture_output=True,
                    cwd=str(cwd),
                )
            finally:
                try:
                    tmp_path.unlink()
                except OSError:
                    pass
        else:
            ruff_proc = subprocess.run(
                ["ruff", "check", str(source_path)],
                text=True,
                capture_output=True,
                cwd=str(cwd),
            )

        checks.append(
            {
                "name": "ruff",
                "ok": ruff_proc.returncode == 0,
                "detail": (ruff_proc.stdout or ruff_proc.stderr or "ok").strip()[:1000],
            }
        )

    return checks


def shutil_which(command: str) -> Optional[str]:
    return subprocess.run(["bash", "-lc", f"command -v {shlex.quote(command)}"], text=True, capture_output=True).stdout.strip() or None


def _run_preflight(command_args: List[str], cwd: pathlib.Path, use_shell: bool) -> Dict[str, Any]:
    preflight_args = list(command_args)
    if use_shell and len(command_args) == 1:
        try:
            preflight_args = shlex.split(command_args[0])
        except ValueError:
            return {
                "ran": False,
                "passed": True,
                "target": None,
                "checks": [{"name": "skip", "ok": True, "detail": "shell command not parseable"}],
            }

    target = _extract_python_target(preflight_args, cwd)
    if target is None:
        return {
            "ran": False,
            "passed": True,
            "target": None,
            "checks": [{"name": "skip", "ok": True, "detail": "non-python command"}],
        }

    checks: List[Dict[str, Any]] = []
    kind = target["kind"]
    value = target["value"]

    if kind == "file":
        source_path = pathlib.Path(value)
        if not source_path.exists():
            checks.append({"name": "file_exists", "ok": False, "detail": f"missing file: {source_path}"})
        else:
            checks.append({"name": "file_exists", "ok": True, "detail": str(source_path)})
            source = source_path.read_text(encoding="utf-8", errors="replace")
            checks.extend(_run_preflight_for_source(source, cwd, source_path))

    elif kind == "inline":
        checks.extend(_run_preflight_for_source(value, cwd, None))

    elif kind == "module":
        module_ok = _module_available(value, cwd)
        checks.append(
            {
                "name": "module_spec",
                "ok": module_ok,
                "detail": f"module {value} {'resolvable' if module_ok else 'not found'}",
            }
        )

    passed = all(bool(check.get("ok")) for check in checks)
    return {
        "ran": True,
        "passed": passed,
        "target": target,
        "checks": checks,
    }


def _format_preflight_failure(preflight: Dict[str, Any]) -> str:
    lines = ["NEXUS preflight failed; command was not executed."]
    for check in preflight.get("checks", []):
        if check.get("ok"):
            continue
        lines.append(f"- {check.get('name')}: {check.get('detail')}")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="nexus_exec",
        description="Run standalone command through NEXUS quality/self-heal pipeline",
    )
    parser.add_argument("--cwd", default=os.getcwd(), help="Working directory for command and hooks")
    parser.add_argument("--shell", action="store_true", help="Execute command through shell")
    parser.add_argument("--skip-preflight", action="store_true", help="Skip static preflight checks")
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

    preflight_result = {
        "ran": False,
        "passed": True,
        "target": None,
        "checks": [{"name": "skip", "ok": True, "detail": "disabled"}],
    }
    if not args.skip_preflight:
        preflight_result = _run_preflight(command_args, cwd, args.shell)

    command_stdout = ""
    command_stderr = ""
    command_rc = 0
    duration = 0.0

    if preflight_result.get("ran") and not preflight_result.get("passed"):
        command_rc = 97
        command_stderr = _format_preflight_failure(preflight_result)
    else:
        start = time.time()
        cmd_proc = subprocess.run(
            command_for_run,
            cwd=str(cwd),
            text=True,
            capture_output=True,
            shell=args.shell,
        )
        duration = time.time() - start
        command_rc = cmd_proc.returncode
        command_stdout = cmd_proc.stdout
        command_stderr = cmd_proc.stderr

    if not args.json_only:
        if command_stdout:
            sys.stdout.write(command_stdout)
        if command_stderr:
            sys.stderr.write(command_stderr)

    event = _build_event(
        command_str=command_str,
        cwd=cwd,
        rc=command_rc,
        stdout=command_stdout,
        stderr=command_stderr,
        duration=duration,
        preflight=preflight_result,
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
    if command_rc != 0:
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

    overall_exit = command_rc
    if overall_exit == 0 and quality_gate_result.get("exit_code", 0) != 0:
        overall_exit = int(quality_gate_result.get("exit_code", 0))

    summary = {
        "timestamp": _now_iso(),
        "cwd": str(cwd),
        "command": command_str,
        "preflight": preflight_result,
        "command_exit_code": command_rc,
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
