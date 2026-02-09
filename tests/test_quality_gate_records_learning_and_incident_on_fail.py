#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from test_utils import git_commit_all, init_git_repo, prepare_sandbox, read_json, read_jsonl, run_python


def run_test() -> None:
    sandbox = prepare_sandbox()
    home = sandbox["home"]
    claude = sandbox["claude"]

    project = sandbox["root"] / "project"
    project.mkdir(parents=True, exist_ok=True)

    (project / "app.py").write_text("def ok():\n    return 1\n")
    init_git_repo(project)
    git_commit_all(project, "initial")

    # Guaranteed quality gate failure via syntax error.
    (project / "app.py").write_text("import os\n\ndef broken(:\n    return 1\n")

    payload = {
        "tool_name": "Edit",
        "tool_input": {"file_path": "app.py"},
        "tool_response": {"success": True},
        "cwd": str(project),
    }

    proc = run_python(claude / "hooks" / "quality_gate.py", home=home, cwd=project, payload=payload)
    assert proc.returncode == 2, proc.stdout + "\n" + proc.stderr

    incidents = read_jsonl(claude / "state" / "incidents.jsonl")
    queue = read_jsonl(claude / "state" / "fix_queue.jsonl")
    learning = read_json(claude / "state" / "learning_patterns.json")

    assert len(incidents) >= 1
    assert len(queue) >= 1

    patterns = learning.get("patterns", {})
    assert "quality_gate_fail" in patterns


if __name__ == "__main__":
    run_test()
    print("PASS test_quality_gate_records_learning_and_incident_on_fail")
