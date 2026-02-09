#!/usr/bin/env python3
from __future__ import annotations

import io
import json
import os
import sys
from pathlib import Path

from test_utils import prepare_sandbox


def run_test() -> None:
    sandbox = prepare_sandbox()
    home = sandbox["home"]
    os.environ["HOME"] = str(home)

    sys.path.insert(0, str(sandbox["claude"] / "hooks"))
    import _hook_io  # type: ignore

    project_dir = sandbox["root"] / "project"
    project_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "tool_name": "Edit",
        "tool_input": {"file_path": "src/main.py"},
        "tool_response": {"success": True},
        "cwd": str(project_dir),
        "extra_field": {"future": "schema"},
    }

    original_stdin = sys.stdin
    try:
        sys.stdin = io.StringIO(json.dumps(payload))
        event = _hook_io.read_hook_event()
    finally:
        sys.stdin = original_stdin

    assert event.get("tool_name") == "Edit"
    assert event.get("tool_input", {}).get("file_path") == "src/main.py"
    assert event.get("tool_response", {}).get("success") is True

    project_root = _hook_io.get_project_root(event)
    assert project_root == project_dir.resolve()


if __name__ == "__main__":
    run_test()
    print("PASS test_hook_io_parsing")
