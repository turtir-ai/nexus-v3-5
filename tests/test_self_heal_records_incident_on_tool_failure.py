#!/usr/bin/env python3
from __future__ import annotations

from test_utils import prepare_sandbox, read_jsonl, run_python


def run_test() -> None:
    sandbox = prepare_sandbox()
    home = sandbox["home"]
    claude = sandbox["claude"]

    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": "python3 broken.py"},
        "tool_response": {
            "success": False,
            "exit_code": 1,
            "stderr": "Permission denied: /tmp/secret.txt",
        },
        "cwd": "/tmp/project",
    }

    proc = run_python(claude / "hooks" / "nexus_self_heal.py", home=home, payload=payload)
    assert proc.returncode == 0, proc.stdout + "\n" + proc.stderr

    incidents = read_jsonl(claude / "state" / "incidents.jsonl")
    queue = read_jsonl(claude / "state" / "fix_queue.jsonl")

    assert len(incidents) == 1
    assert incidents[0].get("incident_class") == "permission_denied"
    assert len(queue) == 1


if __name__ == "__main__":
    run_test()
    print("PASS test_self_heal_records_incident_on_tool_failure")
