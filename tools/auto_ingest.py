"""Automatic ingestion watcher and orchestrator.

Behavior:
- Scan `documents/` and run `tools.ingest_and_classify.classify_and_copy` to sort documents.
- If files were moved, create a temporary branch, commit the changes as a temporary commit, format a patch to `tools/`.
- Call `tools/self_upgrade.py --apply-patch <patch> --run-tests --backtest-cmd "python backtest.py"` with an explicit branch name.
- If `auto_push` and `auto_create_pr` are enabled in `automation.yaml`, push and create PR via `tools.pr_helper`.

Safety: requires a clean working tree before running. Requires `git` and optional `GITHUB_TOKEN` for PR automation.
"""

import argparse
import logging
import os
import subprocess
import sys
import datetime
from pathlib import Path
import shutil
import json

# ensure repo root on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from tools.ingest_and_classify import classify_and_copy

try:
    import yaml
except Exception:
    yaml = None

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

CONFIG_PATH = "automation.yaml"


def run(cmd, check=True, capture=False, cwd=None):
    logging.info(f"$ {cmd}")
    res = subprocess.run(cmd, shell=True, cwd=cwd, text=True, capture_output=capture)
    if capture:
        return res.returncode, res.stdout, res.stderr
    if check and res.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}\nExit {res.returncode}\n{res.stderr}")
    return res.returncode


def load_config(path: Path):
    if not path.exists():
        logging.warning("No automation config found; using defaults.")
        return {
            'auto_push': True,
            'auto_create_pr': True,
            'auto_merge': False,
            'target_branch': 'main',
            'high': 0.80,
            'mid': 0.50,
            'backtest_cmd': 'python backtest.py',
            'watch_path': 'documents',
            'schedule': '6h'
        }
    if yaml:
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    else:
        # try JSON as fallback
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)


def git_current_branch():
    rc, out, _ = run("git rev-parse --abbrev-ref HEAD", capture=True)
    return out.strip()


def git_clean_check():
    rc, out, _ = run("git status --porcelain", capture=True)
    return not bool(out.strip())


def create_temp_patch(tmp_branch: str, tools_out_dir: str = "tools") -> Path:
    # assumes working tree has the new files (uncommitted)
    # create temp branch
    run(f"git checkout -b {tmp_branch}")
    run("git add -A")
    run("git commit -m \"tmp: auto-ingest commit\"")
    # create format-patch
    run(f"git format-patch -1 -o {tools_out_dir}")
    # find the patch file
    files = sorted(Path(tools_out_dir).glob("*.patch"), key=lambda p: p.stat().st_mtime)
    if not files:
        raise RuntimeError("Patch creation failed: no patch found in tools/")
    patch = files[-1]
    logging.info(f"Created patch: {patch}")
    # return to previous branch and delete tmp branch
    prev = git_current_branch()
    # we are on tmp_branch currently, so checkout previous by checking out origin/HEAD's branch
    run("git checkout -")
    run(f"git branch -D {tmp_branch}")
    return patch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=CONFIG_PATH)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--auto", action="store_true", help="Run fully automated flow (create patch, call self_upgrade, push and create PR if enabled)")
    args = parser.parse_args()

    cfg = load_config(Path(args.config))

    if not git_clean_check():
        logging.error("Working tree is not clean. Commit or stash changes before running auto_ingest.")
        sys.exit(1)

    src = Path(cfg.get('watch_path', 'documents'))
    dst = Path('documents/sorted')

    logging.info(f"Scanning {src} -> {dst} (dry={args.dry_run})")
    total, moved = classify_and_copy(src, dst, dry_run=args.dry_run, auto_move=True)
    logging.info(f"Total files scanned: {total}, moved: {moved}")

    if moved == 0:
        logging.info("No files moved; nothing to do.")
        return

    if not args.auto:
        logging.info("Auto flag not set; exiting after move. Run with --auto to proceed with patch and PR creation.")
        return

    ts = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    tmp_branch = f"tmp/auto-ingest-{ts}"
    patch = create_temp_patch(tmp_branch)

    # run self_upgrade with explicit branch name so we can reference it
    auto_branch = f"ai/auto-ingest-{ts}"
    backtest_cmd = cfg.get('backtest_cmd', 'python backtest.py')
    push_flag = "--push" if cfg.get('auto_push', False) else ""

    try:
        run(f"python tools/self_upgrade.py --branch {auto_branch} --apply-patch {patch} --run-tests --backtest-cmd \"{backtest_cmd}\" {push_flag}")
    except Exception as e:
        logging.error(f"Self-upgrade flow failed: {e}")
        logging.info("Leaving branch for manual inspection.")
        sys.exit(1)

    logging.info("Self-upgrade flow completed. Branch: %s", auto_branch)

    if cfg.get('auto_create_pr', True):
        try:
            from tools.pr_helper import create_pr
            owner_repo = None
            # determine repo from git remote
            rc, out, _ = run("git remote get-url origin", capture=True)
            url = out.strip()
            # try to parse https://github.com/OWNER/REPO.git
            if url.startswith('git@'):
                _, path = url.split(':', 1)
                owner_repo = path.rstrip('.git')
            elif url.startswith('http'):
                owner_repo = '/'.join(url.rstrip('.git').split('/')[-2:])
            else:
                owner_repo = None

            if owner_repo is None:
                logging.warning("Cannot determine owner/repo from origin url; PR creation will open browser instead.")
                create_pr(auto_branch, title=f"Auto ingest: {ts}", body="Automated ingestion and classification")
            else:
                owner, repo = owner_repo.split('/')
                pr = create_pr(auto_branch, title=f"Auto ingest: {ts}", body="Automated ingestion and classification", owner=owner, repo=repo)
                logging.info(f"PR created: {pr}")
        except Exception as e:
            logging.warning(f"PR creation failed or not configured: {e}")


if __name__ == "__main__":
    main()
