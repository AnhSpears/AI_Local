"""
Prototype self-upgrade helper (safe local workflow).

Behaviors:
- create a new git branch (no push by default)
- optionally apply a patch file (git apply)
- run syntax checks and tests (pytest if available)
- run a user-provided backtest command
- never auto-merge; prints next steps to push/create PR

Usage examples:
  python tools/self_upgrade.py --branch ai/proposal-001 --apply-patch proposal.patch --run-tests --backtest-cmd "python backtest.py"

Note: this is a prototype. Review changes before pushing.
"""

import argparse
import subprocess
import sys
import os
import datetime
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def run(cmd, cwd=None, check=True, capture=False):
    logging.info(f"$ {cmd}")
    res = subprocess.run(cmd, shell=True, cwd=cwd, text=True, capture_output=capture)
    if capture:
        return res.returncode, res.stdout, res.stderr
    if check and res.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}\nExit {res.returncode}")
    return res.returncode


def find_git_root():
    p = Path.cwd()
    for _ in range(50):
        if (p / ".git").exists():
            return p
        if p.parent == p:
            break
        p = p.parent
    return None


def main():
    parser = argparse.ArgumentParser(description="Prototype safe self-upgrade local workflow")
    parser.add_argument("--branch", required=False, help="Branch name to create (default ai/auto-<ts>)")
    parser.add_argument("--apply-patch", help="Path to a patch file (git format) to apply on the new branch")
    parser.add_argument("--run-tests", action="store_true", help="Run pytest if available")
    parser.add_argument("--backtest-cmd", help="Optional backtest command to run (shell)")
    parser.add_argument("--push", action="store_true", help="If set, push branch to origin (default: false)")
    args = parser.parse_args()

    git_root = find_git_root()
    if not git_root:
        logging.error("No git repository found in parents of current directory.")
        sys.exit(1)

    os.chdir(git_root)
    ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    branch = args.branch or f"ai/auto-{ts}"

    try:
        # Ensure working tree is clean
        rc, out, err = run("git status --porcelain", capture=True)
        if out.strip():
            logging.error("Working tree is not clean. Commit or stash changes before running this script.")
            logging.info(out)
            sys.exit(1)

        # Create and checkout branch
        run(f"git checkout -b {branch}")

        # Optionally apply patch
        if args.apply_patch:
            patch_path = Path(args.apply_patch)
            if not patch_path.exists():
                logging.error(f"Patch file not found: {patch_path}")
                sys.exit(1)
            try:
                run(f"git apply --index {patch_path}")
                run("git add -A")
                run("git commit -m \"AI: proposed changes (automated)\"")
            except Exception as e:
                logging.error(f"Applying patch failed: {e}")
                logging.info("You can inspect the branch, fix conflicts, and commit manually.")

        # Syntax check: compile all Python files
        try:
            run("python -m compileall -q .")
            logging.info("Syntax check passed.")
        except Exception as e:
            logging.error(f"Syntax check failed: {e}")
            logging.info("Leaving branch for inspection.")
            sys.exit(1)

        # Run tests if requested and pytest present
        if args.run_tests:
            try:
                rc, out, err = run("pytest -q", capture=True)
                if rc == 0:
                    logging.info("Pytest passed.")
                else:
                    logging.error("Pytest reported failures. See output below:")
                    logging.error(out)
                    logging.error(err)
                    logging.info("Leaving branch for inspection.")
                    sys.exit(1)
            except FileNotFoundError:
                logging.warning("pytest not installed or not found; skipping tests.")
            except Exception as e:
                logging.error(f"Running tests failed: {e}")
                sys.exit(1)

        # Run backtest command if provided
        if args.backtest_cmd:
            try:
                logging.info(f"Running backtest: {args.backtest_cmd}")
                run(args.backtest_cmd)
                logging.info("Backtest finished successfully.")
            except Exception as e:
                logging.error(f"Backtest failed: {e}")
                logging.info("Leaving branch for inspection.")
                sys.exit(1)

        logging.info("All checks passed on branch %s.", branch)
        logging.info("Next steps (manual):")
        logging.info(" - Inspect branch locally: git checkout %s", branch)
        logging.info(" - Push branch to remote if desired: git push -u origin %s", branch)
        logging.info(" - Create a PR on GitHub and perform human review before merging.")

        if args.push:
            logging.info("Pushing branch to origin...")
            run(f"git push -u origin {branch}")
            logging.info("Branch pushed. Use GH CLI or GitHub UI to open a PR.")

    except Exception as e:
        logging.error(f"Error during self-upgrade workflow: {e}")
        logging.info("You can switch back to main: git checkout main (or original branch)")
        sys.exit(1)


if __name__ == "__main__":
    main()
