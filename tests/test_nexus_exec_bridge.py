#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from test_utils import git_commit_all, init_git_repo, prepare_sandbox, read_jsonl, run_python


def run_test() -> None:
    sandbox = prepare_sandbox()
    home = sandbox["home"]
    claude = sandbox["claude"]

    project = sandbox["root"] / "standalone_project"
    project.mkdir(parents=True, exist_ok=True)

    (project / "main.py").write_text("def ok():\n    return 1\n")
    init_git_repo(project)
    git_commit_all(project, "initial")

    incidents_before = len(read_jsonl(claude / "state" / "incidents.jsonl"))
    fix_before = len(read_jsonl(claude / "state" / "fix_queue.jsonl"))

    # Use bridge to run a failing standalone command.
    proc = run_python(
        claude / "nexus_exec.py",
        home=home,
        cwd=project,
        args=["--", "python3", "-c", "import definitely_missing_module_bridge"],
    )

    assert proc.returncode != 0, proc.stdout + "\n" + proc.stderr

    incidents_after = len(read_jsonl(claude / "state" / "incidents.jsonl"))
    fix_after = len(read_jsonl(claude / "state" / "fix_queue.jsonl"))

    assert incidents_after > incidents_before, (incidents_before, incidents_after, proc.stdout)
    assert fix_after > fix_before, (fix_before, fix_after, proc.stdout)


if __name__ == "__main__":
    run_test()
    print("PASS test_nexus_exec_bridge")
