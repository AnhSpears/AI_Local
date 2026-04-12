#!/usr/bin/env python3
"""A tiny autonomous assistant loop with safety-minded local actions."""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass
class Step:
    action: str
    payload: dict


def simple_planner(goal: str, iteration: int) -> Step:
    """Deterministic planner stub; replace with model-driven planning as needed."""
    goal_lower = goal.lower()

    if iteration == 0 and "plan" in goal_lower:
        target = "plan.txt"
        content = f"Goal: {goal}\n- Research audience\n- Draft outline\n- Publish MVP\n"
        return Step("write_file", {"path": target, "content": content})

    if iteration == 1:
        return Step("read_file", {"path": "plan.txt"})

    return Step("finish", {"reason": "Goal appears satisfied by starter loop."})


def run_command(cmd: str) -> str:
    allowlist = {"pwd", "ls", "cat", "echo"}
    base = cmd.split()[0] if cmd.strip() else ""
    if base not in allowlist:
        return f"Blocked command '{base}'. Allowed: {sorted(allowlist)}"

    proc = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    return (proc.stdout + proc.stderr).strip()


def execute(step: Step) -> str:
    def write_file(payload: dict) -> str:
        Path(payload["path"]).write_text(payload["content"], encoding="utf-8")
        return f"Wrote {payload['path']}"

    handlers: dict[str, Callable[[dict], str]] = {
        "write_file": write_file,
        "read_file": lambda p: Path(p["path"]).read_text(encoding="utf-8"),
        "run_command": lambda p: run_command(p["cmd"]),
        "finish": lambda p: f"Finished: {p.get('reason', 'no reason provided')}",
    }

    if step.action not in handlers:
        return f"Unknown action: {step.action}"

    try:
        result = handlers[step.action](step.payload)
        return result if isinstance(result, str) else str(result)
    except Exception as exc:  # defensive error surfacing for loop visibility
        return f"Execution error: {exc}"


def autonomous_loop(goal: str, max_iters: int = 5) -> list[dict]:
    history: list[dict] = []

    for i in range(max_iters):
        step = simple_planner(goal, i)
        observation = execute(step)
        history.append(
            {
                "iteration": i,
                "step": {"action": step.action, "payload": step.payload},
                "observation": observation,
            }
        )
        if step.action == "finish":
            break

    return history


def main() -> None:
    parser = argparse.ArgumentParser(description="Autonomous AI assistant starter loop")
    parser.add_argument("goal", help="High-level objective for the assistant")
    parser.add_argument("--max-iters", type=int, default=5, help="Maximum planning iterations")
    args = parser.parse_args()

    history = autonomous_loop(args.goal, max_iters=args.max_iters)
    print(json.dumps(history, indent=2))


if __name__ == "__main__":
    main()
