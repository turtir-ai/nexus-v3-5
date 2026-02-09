#!/usr/bin/env python3
"""
NEXUS V3.5.0 - Agent Runtime Engine
Deterministic runtime primitives used by hooks and dispatcher.
"""
import json
import os
import sys
import pathlib
import subprocess
from datetime import datetime
from typing import Dict, Any, List
from dataclasses import dataclass
import time

try:
    import tomllib
except ImportError:  # pragma: no cover
    tomllib = None

# Add state manager to path
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from state_manager import get_state_manager
try:
    from hooks.fix_queue import FixQueue
    FIX_QUEUE_AVAILABLE = True
except ImportError:
    try:
        # Direct import from hooks directory
        import importlib.util
        spec = importlib.util.spec_from_file_location("fix_queue", pathlib.Path(__file__).parent / "hooks" / "fix_queue.py")
        fix_queue_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fix_queue_module)
        FixQueue = fix_queue_module.FixQueue
        FIX_QUEUE_AVAILABLE = True
    except:
        FIX_QUEUE_AVAILABLE = False


@dataclass
class AgentMessage:
    """Message between agents"""
    sender: str
    receiver: str
    msg_type: str  # request, response, alert, command
    content: Dict[str, Any]
    timestamp: str
    id: str

    def to_dict(self):
        return {
            "sender": self.sender,
            "receiver": self.receiver,
            "type": self.msg_type,
            "content": self.content,
            "timestamp": self.timestamp,
            "id": self.id
        }


class AgentBus:
    """Real message bus for agent communication"""

    def __init__(self):
        self.messages: List[AgentMessage] = []
        self.message_log = pathlib.Path.home() / ".claude" / "state" / "agent_messages.jsonl"

    def send(self, sender: str, receiver: str, msg_type: str, content: Dict[str, Any]) -> str:
        """Send message from one agent to another"""
        msg = AgentMessage(
            sender=sender,
            receiver=receiver,
            msg_type=msg_type,
            content=content,
            timestamp=datetime.now().isoformat(),
            id=f"msg_{int(time.time() * 1000)}"
        )
        self.messages.append(msg)

        # Log to file
        with self.message_log.open("a") as f:
            f.write(json.dumps(msg.to_dict()) + "\n")

        return msg.id

    def get_messages_for(self, agent: str) -> List[AgentMessage]:
        """Get messages for a specific agent"""
        return [m for m in self.messages if m.receiver == agent]

    def broadcast(self, sender: str, msg_type: str, content: Dict[str, Any]):
        """Send to all agents"""
        agents = ["nexus", "pilot", "guardian", "healer", "discover"]
        for agent in agents:
            if agent != sender:
                self.send(sender, agent, msg_type, content)


class BaseAgent:
    """Base class for all agents"""

    def __init__(self, name: str, bus: AgentBus, state_manager):
        self.name = name
        self.bus = bus
        self.state = state_manager
        self.status = "idle"

    def receive(self) -> List[AgentMessage]:
        """Get pending messages"""
        return self.bus.get_messages_for(self.name)

    def send(self, receiver: str, msg_type: str, content: Dict[str, Any]):
        """Send message to another agent"""
        return self.bus.send(self.name, receiver, msg_type, content)

    def broadcast(self, msg_type: str, content: Dict[str, Any]):
        """Broadcast to all agents"""
        self.bus.broadcast(self.name, msg_type, content)

    def execute(self, task: str) -> Dict[str, Any]:
        """Execute a task (override in subclasses)"""
        return {"status": "not_implemented", "agent": self.name}


class DiscoverAgent(BaseAgent):
    """Auto-discovery agent - runs automatically"""

    IGNORE_DIRS = {".git", "node_modules", ".venv", "dist", "build", "__pycache__", ".next"}
    LANGUAGE_MAP = {
        ".py": "Python",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".tsx": "TypeScript",
        ".jsx": "JavaScript",
        ".go": "Go",
        ".java": "Java",
        ".rs": "Rust",
        ".rb": "Ruby",
        ".php": "PHP",
        ".md": "Markdown",
        ".json": "JSON",
        ".yml": "YAML",
        ".yaml": "YAML",
    }

    def __init__(self, bus: AgentBus, state_manager):
        super().__init__("discover", bus, state_manager)

    def _iter_project_files(self, root: pathlib.Path):
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [name for name in dirnames if name not in self.IGNORE_DIRS]
            for filename in filenames:
                yield pathlib.Path(dirpath) / filename

    def _collect_dependency_hints(self, root: pathlib.Path) -> Dict[str, Any]:
        hints: Dict[str, Any] = {
            "python": {"requirements_files": [], "dependencies": []},
            "node": {"dependencies": [], "dev_dependencies": []},
        }

        for req_file in sorted(root.glob("requirements*.txt")):
            try:
                deps = []
                for line in req_file.read_text().splitlines():
                    value = line.strip()
                    if not value or value.startswith("#"):
                        continue
                    deps.append(value)
                hints["python"]["requirements_files"].append(req_file.name)
                hints["python"]["dependencies"].extend(deps[:30])
            except OSError:
                continue

        pyproject = root / "pyproject.toml"
        if pyproject.exists() and tomllib is not None:
            try:
                content = tomllib.loads(pyproject.read_text())
                project_deps = content.get("project", {}).get("dependencies", [])
                if isinstance(project_deps, list):
                    hints["python"]["dependencies"].extend(project_deps[:30])

                poetry_deps = content.get("tool", {}).get("poetry", {}).get("dependencies", {})
                if isinstance(poetry_deps, dict):
                    hints["python"]["dependencies"].extend(list(poetry_deps.keys())[:30])
            except Exception:
                pass

        package_json = root / "package.json"
        if package_json.exists():
            try:
                package_data = json.loads(package_json.read_text())
                deps = package_data.get("dependencies", {})
                dev_deps = package_data.get("devDependencies", {})
                if isinstance(deps, dict):
                    hints["node"]["dependencies"] = list(deps.keys())[:40]
                if isinstance(dev_deps, dict):
                    hints["node"]["dev_dependencies"] = list(dev_deps.keys())[:40]
            except (json.JSONDecodeError, OSError):
                pass

        return hints

    def _project_type(self, ext_counts: Dict[str, int], root: pathlib.Path) -> str:
        has_python = ".py" in ext_counts or (root / "pyproject.toml").exists() or (root / "requirements.txt").exists()
        has_node = ".js" in ext_counts or ".ts" in ext_counts or (root / "package.json").exists()
        if has_python and has_node:
            return "mixed"
        if has_python:
            return "python"
        if has_node:
            return "node"
        return "unknown"

    def auto_scan(self):
        """Auto-scan current project with deterministic file/language discovery."""
        cwd = pathlib.Path.cwd()
        file_count = 0
        ext_counts: Dict[str, int] = {}
        language_counts: Dict[str, int] = {}

        for file_path in self._iter_project_files(cwd):
            file_count += 1
            suffix = file_path.suffix.lower() or "<no_ext>"
            ext_counts[suffix] = ext_counts.get(suffix, 0) + 1

            language = self.LANGUAGE_MAP.get(suffix)
            if language:
                language_counts[language] = language_counts.get(language, 0) + 1

        top_dirs = sorted(
            [
                child.name
                for child in cwd.iterdir()
                if child.is_dir() and child.name not in self.IGNORE_DIRS
            ]
        )
        dependency_hints = self._collect_dependency_hints(cwd)
        project_type = self._project_type(ext_counts, cwd)

        result = {
            "project": str(cwd),
            "scanned_at": datetime.now().isoformat(),
            "file_count": file_count,
            "files": file_count,
            "languages": language_counts,
            "extensions": ext_counts,
            "top_level_directories": top_dirs,
            "dependency_hints": dependency_hints,
            "project_type": project_type,
        }

        # Update mental model
        mental_model = self.state.load_mental_model()
        mental_model["current_project"] = str(cwd)
        mental_model["last_scan"] = {
            "timestamp": datetime.now().isoformat(),
            "cwd": str(cwd),
            "file_count": file_count,
        }
        mental_model["projects"][str(cwd)] = {
            "scanned_at": result["scanned_at"],
            "file_count": file_count,
            "files": file_count,
            "languages": language_counts,
            "extensions": ext_counts,
            "top_level_directories": top_dirs,
            "dependency_hints": dependency_hints,
            "project_type": project_type,
        }
        self.state.save_mental_model(mental_model)

        metrics = self.state.load_metrics()
        discover_metrics = metrics.get("agent_performance", {}).get("discover", {})
        discover_metrics["scans"] = int(discover_metrics.get("scans", 0)) + 1
        discover_metrics["patterns_found"] = len(language_counts)
        metrics["agent_performance"]["discover"] = discover_metrics
        self.state.save_metrics(metrics)

        # Broadcast discovery
        self.broadcast("discovery_complete", result)

        return result


class GuardianAgent(BaseAgent):
    """Guardian agent - monitors operations"""

    def __init__(self, bus: AgentBus, state_manager):
        super().__init__("guardian", bus, state_manager)
        self.alerts_raised = 0
        self.issues_prevented = 0

    def evaluate_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate if action is safe"""
        tool = action.get("tool", "")

        # Destructive actions
        if tool in ["Delete", "ForcePush"]:
            self.alerts_raised += 1
            return {
                "allowed": False,
                "reason": "Destructive action requires approval",
                "level": "RED"
            }

        # Credential access
        if "password" in str(action).lower() or "secret" in str(action).lower():
            self.alerts_raised += 1
            return {
                "allowed": False,
                "reason": "Credential access requires approval",
                "level": "RED"
            }

        # Large scale edit
        if tool == "Edit":
            file_path = action.get("file_path", "")
            if file_path:
                # Check file size
                try:
                    size = pathlib.Path(file_path).stat().st_size
                    if size > 100000:  # 100KB
                        return {
                            "allowed": True,
                            "warning": "Large file edit",
                            "level": "YELLOW"
                        }
                except:
                    pass

        return {"allowed": True, "level": "GREEN"}


class PilotAgent(BaseAgent):
    """Pilot agent - executes tasks"""

    def __init__(self, bus: AgentBus, state_manager):
        super().__init__("pilot", bus, state_manager)
        self.tasks_completed = 0

    def execute(self, task: str) -> Dict[str, Any]:
        """Execute a task"""
        self.status = "working"

        result = {
            "task": task,
            "status": "in_progress",
            "steps": []
        }

        # Update MSV
        self.state.update_msv({
            "confidence": 0.7,
            "progress": 0.3
        })

        # Ask guardian first
        guardian = GuardianAgent(self.bus, self.state)
        evaluation = guardian.evaluate_action({"tool": "unknown", "task": task})

        if not evaluation.get("allowed"):
            result["status"] = "blocked"
            result["reason"] = evaluation.get("reason")
            return result

        # Execute (simplified - real execution would call Claude)
        result["status"] = "completed"
        self.tasks_completed += 1

        # Update metrics
        metrics = self.state.load_metrics()
        metrics["agent_performance"]["pilot"]["tasks"] = self.tasks_completed
        self.state.save_metrics(metrics)

        self.status = "idle"
        return result


class NexusRuntime:
    """Main NEXUS runtime - orchestrates all agents"""

    def __init__(self):
        self.state = get_state_manager()
        self.bus = AgentBus()
        self.agents = {}

        # Initialize agents
        self.agents["discover"] = DiscoverAgent(self.bus, self.state)
        self.agents["guardian"] = GuardianAgent(self.bus, self.state)
        self.agents["pilot"] = PilotAgent(self.bus, self.state)

        # Load state
        self.msv = self.state.load_msv()

    def start(self):
        """Start NEXUS runtime"""
        # Auto-discover current project
        discover_result = self.agents["discover"].auto_scan()

        # Update MSV
        self.state.update_msv({
            "confidence": 0.7,
            "resource_utilization": 0.1
        })

        # Record start
        self.state.record_event("nexus_start", {
            "runtime_version": "3.5.0",
            "agents": list(self.agents.keys())
        })

        return {
            "status": "active",
            "discover": discover_result,
            "agents": list(self.agents.keys()),
            "msv": self.msv["state_vector"]
        }

    def execute_task(self, task: str) -> Dict[str, Any]:
        """Execute a task through NEXUS"""
        # Send to pilot
        result = self.agents["pilot"].execute(task)

        # Record execution
        self.state.record_event("task_execution", {
            "task": task,
            "result": result
        })

        return result

    def process_fix_queue(self) -> Dict[str, Any]:
        """Process exactly one pending fix task via deterministic verify command."""
        if not FIX_QUEUE_AVAILABLE:
            return {"status": "fix_queue_not_available"}

        fix_queue = FixQueue()
        return fix_queue.process_one_task(executor="runtime")

    def get_status(self) -> Dict[str, Any]:
        """Get current runtime status"""
        status = {
            "runtime_version": "3.5.0",
            "agents": {
                name: agent.status for name, agent in self.agents.items()
            },
            "msv": self.state.load_msv()["state_vector"],
            "metrics": self.state.load_metrics()["agent_performance"],
            "message_count": len(self.bus.messages)
        }

        if FIX_QUEUE_AVAILABLE:
            fix_queue = FixQueue()
            status["fix_queue"] = fix_queue.get_stats()

        return status


def main():
    """Run NEXUS runtime"""
    runtime = NexusRuntime()

    # Start
    status = runtime.start()
    print(json.dumps(status, indent=2))

    # Get status
    status_report = runtime.get_status()
    print("\n=== NEXUS V3.5.0 RUNTIME STATUS ===")
    print(json.dumps(status_report, indent=2))


if __name__ == "__main__":
    main()
