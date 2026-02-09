#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

REAL_CLAUDE = Path.home() / ".claude"

FILES_TO_COPY = [
    "state_manager.py",
    "task_manager.py",
    "nexus_cli.py",
    "agent_runtime.py",
    "generate_quality_report.py",
    "hooks/_hook_io.py",
    "hooks/quality_gate.py",
    "hooks/fix_queue.py",
    "hooks/nexus_self_heal.py",
    "hooks/nexus_auto_learn.py",
    "hooks/audit_logger.py",
    "hooks/nexus_agent_dispatcher.py",
]


def prepare_sandbox() -> Dict[str, Path]:
    root = Path(tempfile.mkdtemp(prefix="nexus_test_"))
    home = root / "home"
    home.mkdir(parents=True, exist_ok=True)

    claude = home / ".claude"
    (claude / "hooks").mkdir(parents=True, exist_ok=True)
    (claude / "state").mkdir(parents=True, exist_ok=True)
    (claude / "logs").mkdir(parents=True, exist_ok=True)

    for relative in FILES_TO_COPY:
        source = REAL_CLAUDE / relative
        target = claude / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    return {
        "root": root,
        "home": home,
        "claude": claude,
    }


def run_python(
    script: Path,
    home: Path,
    cwd: Optional[Path] = None,
    payload: Optional[Dict[str, Any]] = None,
    args: Optional[List[str]] = None,
    timeout: int = 120,
) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["HOME"] = str(home)

    cmd = ["python3", str(script)]
    if args:
        cmd.extend(args)

    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        input=json.dumps(payload) if payload is not None else "",
        text=True,
        capture_output=True,
        env=env,
        timeout=timeout,
    )


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text())


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        rows.append(json.loads(line))
    return rows


def init_git_repo(project_dir: Path) -> None:
    subprocess.run(["git", "init"], cwd=project_dir, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "nexus@test.local"], cwd=project_dir, check=True)
    subprocess.run(["git", "config", "user.name", "Nexus Test"], cwd=project_dir, check=True)


def git_commit_all(project_dir: Path, message: str) -> None:
    subprocess.run(["git", "add", "."], cwd=project_dir, check=True)
    subprocess.run(["git", "commit", "-m", message], cwd=project_dir, check=True, capture_output=True, text=True)
