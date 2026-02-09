#!/usr/bin/env python3
"""Shared IO helpers for Claude Code hooks."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def now_iso() -> str:
    """UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def get_claude_dir() -> Path:
    """Return the default Claude directory."""
    return Path.home() / ".claude"


def safe_write_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    """Append one JSON object as a line without raising caller-facing errors."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(obj, ensure_ascii=False, default=str) + "\n")


def _debug_log(entry: Dict[str, Any]) -> None:
    debug_file = get_claude_dir() / "logs" / "hook_io_debug.jsonl"
    payload = {"timestamp": now_iso(), **entry}
    safe_write_jsonl(debug_file, payload)


def read_hook_event() -> Dict[str, Any]:
    """
    Read stdin and parse hook payload.

    Returns:
      - parsed dict for valid JSON object
      - {} for empty/unparseable payload (also logged for debugging)
    """
    raw = sys.stdin.read()
    if not raw or not raw.strip():
        _debug_log({"event": "empty_stdin"})
        return {}

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        _debug_log(
            {
                "event": "invalid_json",
                "error": str(exc),
                "raw_payload": raw[:8000],
            }
        )
        return {}

    if not isinstance(data, dict):
        _debug_log({"event": "non_object_json", "raw_payload": raw[:8000]})
        return {}

    # Backward-compatible canonical fields used by hooks.
    if "tool_name" not in data and "tool" in data:
        data["tool_name"] = data.get("tool")
    if "tool_input" not in data:
        data["tool_input"] = (
            data.get("tool_input")
            or data.get("params")
            or data.get("input")
            or {}
        )
    if "tool_response" not in data:
        data["tool_response"] = data.get("tool_response") or data.get("result") or {}
    if "cwd" not in data:
        data["cwd"] = os.environ.get("PWD")

    data.setdefault("raw_payload", raw)
    return data


def get_project_root(event: Dict[str, Any]) -> Path:
    """Resolve project root from hook event with robust fallbacks."""
    candidates = []
    if isinstance(event, dict):
        candidates.append(event.get("cwd"))
    candidates.append(os.environ.get("PWD"))
    candidates.append(os.getcwd())

    for value in candidates:
        if not value:
            continue
        try:
            path = Path(value).expanduser().resolve()
            if path.exists():
                return path
        except OSError:
            continue

    return Path.cwd().resolve()
