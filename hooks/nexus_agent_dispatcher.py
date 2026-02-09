#!/usr/bin/env python3
"""NEXUS V3.5.0 deterministic agent dispatcher."""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from datetime import datetime, timezone
from typing import Any, Dict

from _hook_io import get_project_root, read_hook_event

CLAUDE_DIR = pathlib.Path.home() / ".claude"
sys.path.insert(0, str(CLAUDE_DIR))

from agent_runtime import AgentBus
from state_manager import get_state_manager

ROUTE_BY_TYPE = {
    "scan": "discover",
    "safety": "guardian",
    "fix": "pilot",
    "implement": "pilot",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def select_agent(task: Dict[str, Any]) -> str:
    task_type = str(task.get("type", "implement")).strip().lower()
    return ROUTE_BY_TYPE.get(task_type, "pilot")


def build_action_plan(agent: str, task: Dict[str, Any], message_id: str) -> Dict[str, Any]:
    task_type = str(task.get("type", "implement")).strip().lower()
    goal = task.get("goal") or task.get("description") or "unspecified"

    if agent == "discover":
        steps = [
            "Scan project tree with ignore rules",
            "Update mental_model.json with language/dependency summary",
            "Return scan summary",
        ]
    elif agent == "guardian":
        steps = [
            "Evaluate safety constraints for requested action",
            "Return allow/deny with reasons",
            "If denied, propose safer alternative",
        ]
    else:
        steps = [
            "Plan minimal implementation/fix steps",
            "Execute changes through normal tool flow",
            "Rely on quality gate results for completion evidence",
        ]

    return {
        "message_id": message_id,
        "agent": agent,
        "task_type": task_type,
        "goal": goal,
        "steps": steps,
        "created_at": _now_iso(),
        "deterministic": True,
    }


def dispatch(task: Dict[str, Any], sender: str = "nexus") -> Dict[str, Any]:
    bus = AgentBus()
    sm = get_state_manager()

    agent = select_agent(task)
    outbound_content = {
        "task": task,
        "dispatched_at": _now_iso(),
    }
    message_id = bus.send(sender=sender, receiver=agent, msg_type="task_dispatch", content=outbound_content)

    action_plan = build_action_plan(agent=agent, task=task, message_id=message_id)
    response_id = bus.send(sender=agent, receiver=sender, msg_type="action_plan", content=action_plan)

    record = {
        "status": "dispatched",
        "agent": agent,
        "message_id": message_id,
        "response_message_id": response_id,
        "action_plan": action_plan,
    }
    sm.record_event("agent_dispatch", record)
    return record


def evaluate_msv_and_dispatch(event: Dict[str, Any]) -> Dict[str, Any]:
    sm = get_state_manager()
    msv = sm.load_msv()
    cwd = str(get_project_root(event))

    tasks = [
        {
            "type": "scan",
            "goal": "refresh_project_scan",
            "cwd": cwd,
            "trigger": "session_start",
        }
    ]

    if msv.get("state_vector", {}).get("blocked"):
        tasks.append(
            {
                "type": "fix",
                "goal": "resolve_blocking_incident",
                "cwd": cwd,
                "trigger": "state_blocked",
            }
        )

    dispatched = [dispatch(task) for task in tasks]
    return {"evaluated": True, "tasks": tasks, "dispatched": dispatched}


def _parse_task_arg(task_arg: str) -> Dict[str, Any]:
    try:
        data = json.loads(task_arg)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    return {"type": "implement", "goal": task_arg}


def main() -> int:
    parser = argparse.ArgumentParser(description="NEXUS deterministic dispatcher")
    parser.add_argument("command", choices=["evaluate", "dispatch"], nargs="?", default="evaluate")
    parser.add_argument("task", nargs="?", default="")
    args = parser.parse_args()

    event = read_hook_event()

    if args.command == "evaluate":
        result = evaluate_msv_and_dispatch(event)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    task = _parse_task_arg(args.task) if args.task else {
        "type": "implement",
        "goal": "unspecified",
        "cwd": str(get_project_root(event)),
    }
    result = dispatch(task)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
