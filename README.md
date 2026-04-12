# Autonomous AI Assistant (Starter)

This repository contains a lightweight, local-first starter for an **autonomous AI assistant** loop.

## What it does

- Accepts a high-level goal from the user.
- Plans small actionable steps.
- Executes safe local actions (file write/read and shell commands).
- Reflects on command output and continues until a stop condition.

## Quickstart

```bash
python3 assistant.py "Create a project plan in plan.txt for launching a newsletter"
```

## Notes

- This is a starter implementation intended for experimentation.
- Shell command execution is intentionally restricted to a small allowlist.
- Extend the planner/executor with your preferred model provider.
