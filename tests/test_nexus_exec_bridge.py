#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from test_utils import git_commit_all, init_git_repo, prepare_sandbox, read_jsonl, run_python


def run_test() -> None:
    sandbox = prepare_sandbox()
    home = sandbox["home"]
    claude = sandbox["claude"]

    project = sandbox["root"] / "standalone_project"
    project.mkdir(parents=True, exist_ok=True)

    # Missing import should be caught by preflight without executing command.
    (project / "main.py").write_text("import definitely_missing_module_bridge\n\nprint('should_not_run')\n")
    init_git_repo(project)
    git_commit_all(project, "initial")

    incidents_before = len(read_jsonl(claude / "state" / "incidents.jsonl"))
    fix_before = len(read_jsonl(claude / "state" / "fix_queue.jsonl"))

    # Use bridge to run a failing standalone command.
    proc = run_python(
        claude / "nexus_exec.py",
        home=home,
        cwd=project,
        args=["--", "python3", "main.py"],
    )

    assert proc.returncode != 0, proc.stdout + "\n" + proc.stderr
    summary = json.loads(proc.stdout)
    assert summary.get("preflight", {}).get("ran") is True
    assert summary.get("preflight", {}).get("passed") is False
    assert int(summary.get("command_exit_code", 0)) == 97
    assert "missing imports" in (proc.stderr + proc.stdout).lower()

    incidents_after = len(read_jsonl(claude / "state" / "incidents.jsonl"))
    fix_after = len(read_jsonl(claude / "state" / "fix_queue.jsonl"))

    assert incidents_after > incidents_before, (incidents_before, incidents_after, proc.stdout)
    assert fix_after > fix_before, (fix_before, fix_after, proc.stdout)


if __name__ == "__main__":
    run_test()
    print("PASS test_nexus_exec_bridge")
