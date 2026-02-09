#!/usr/bin/env python3
from __future__ import annotations

import importlib
import traceback
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

TEST_MODULES = [
    "test_hook_io_parsing",
    "test_nexus_exec_bridge",
    "test_quality_gate_records_learning_and_incident_on_fail",
    "test_self_heal_records_incident_on_tool_failure",
    "test_task_manager_metrics",
]


def main() -> int:
    passed = 0
    failed = 0

    for module_name in TEST_MODULES:
        try:
            module = importlib.import_module(module_name)
            module.run_test()
            print(f"PASS {module_name}")
            passed += 1
        except Exception:
            print(f"FAIL {module_name}")
            traceback.print_exc()
            failed += 1

    print(f"\nRESULT: passed={passed} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
