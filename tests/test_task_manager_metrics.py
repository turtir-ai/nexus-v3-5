#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from test_utils import git_commit_all, init_git_repo, prepare_sandbox, read_json, run_python


def run_test() -> None:
    sandbox = prepare_sandbox()
    home = sandbox["home"]
    claude = sandbox["claude"]

    project = sandbox["root"] / "project"
    project.mkdir(parents=True, exist_ok=True)
    (project / "main.py").write_text("def hello():\n    return 'ok'\n")

    init_git_repo(project)
    git_commit_all(project, "initial")

    start_proc = run_python(
        claude / "nexus_cli.py",
        home=home,
        cwd=project,
        args=["task", "start", "Implement deterministic metrics"],
    )
    assert start_proc.returncode == 0, start_proc.stdout + "\n" + start_proc.stderr

    pass_event = {
        "tool_name": "Read",
        "tool_input": {"file_path": "main.py"},
        "tool_response": {"success": True},
        "cwd": str(project),
    }
    gate_proc = run_python(
        claude / "hooks" / "quality_gate.py",
        home=home,
        cwd=project,
        payload=pass_event,
    )
    assert gate_proc.returncode == 0, gate_proc.stdout + "\n" + gate_proc.stderr

    close_proc = run_python(
        claude / "nexus_cli.py",
        home=home,
        cwd=project,
        args=["task", "close", "--success", "--note", "Completed after pass"],
    )
    assert close_proc.returncode == 0, close_proc.stdout + "\n" + close_proc.stderr

    metrics = read_json(claude / "state" / "performance_metrics.json")
    assert int(metrics.get("task_progress_events", 0)) > 0
    assert int(metrics.get("tasks_completed", 0)) > 0
    assert int(metrics.get("tasks_successful", 0)) > 0


if __name__ == "__main__":
    run_test()
    print("PASS test_task_manager_metrics")
