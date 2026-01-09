"""Helpers to create a PR using GitHub REST API or fallback to opening browser.

Usage:
  create_pr(head, title, body, owner=None, repo=None)

Requires GITHUB_TOKEN env var for REST API option. If not present, will open the PR creation URL in the browser.
"""
import os
import requests
import webbrowser
import logging

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


def _api_headers():
    return {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}


def repo_default_branch(owner: str, repo: str):
    url = f"https://api.github.com/repos/{owner}/{repo}"
    r = requests.get(url, headers=_api_headers() if GITHUB_TOKEN else {})
    r.raise_for_status()
    return r.json().get("default_branch", "main")


def create_pr(head: str, title: str, body: str = "", owner: str = None, repo: str = None):
    if owner and repo and GITHUB_TOKEN:
        base = repo_default_branch(owner, repo)
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
        payload = {"title": title, "head": head, "base": base, "body": body}
        r = requests.post(url, json=payload, headers=_api_headers())
        r.raise_for_status()
        pr = r.json()
        return pr.get("html_url")

    # fallback: if repo provided, open create PR page for head
    if owner and repo:
        url = f"https://github.com/{owner}/{repo}/pull/new/{head}"
        webbrowser.open(url)
        return url

    # last fallback: open github.com
    webbrowser.open("https://github.com")
    return "https://github.com"
