#!/usr/bin/env python3
"""Dispatch the macOS release asset workflow for a published tag."""

from __future__ import annotations

import argparse
import json
import os
import urllib.request


API_ROOT = "https://api.github.com/repos"


def parse_repository(repository: str) -> tuple[str, str]:
    """Parse an owner/repo string from GitHub Actions environment."""
    owner, separator, repo = repository.partition("/")
    if not owner or separator != "/" or not repo:
        raise ValueError(f"Invalid GitHub repository: {repository!r}")
    return owner, repo


def dispatch_workflow(
    owner: str,
    repo: str,
    workflow: str,
    ref: str,
    token: str,
    inputs: dict[str, str],
) -> None:
    """Dispatch a GitHub Actions workflow via the REST API."""
    url = f"{API_ROOT}/{owner}/{repo}/actions/workflows/{workflow}/dispatches"
    payload = json.dumps({"ref": ref, "inputs": inputs}).encode("utf-8")
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "battmon-macos",
    }
    request = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status != 204:
            raise RuntimeError(f"Workflow dispatch failed with status {response.status}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Dispatch the release asset workflow.")
    parser.add_argument("--tag", required=True, help="Release tag to package and upload")
    parser.add_argument("--workflow", default="release.yml", help="Workflow file name to dispatch")
    parser.add_argument("--ref", default="main", help="Git ref used to dispatch the workflow")
    parser.add_argument(
        "--repository",
        default=os.environ.get("GITHUB_REPOSITORY", ""),
        help="GitHub repository in owner/repo form",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("GITHUB_TOKEN", ""),
        help="GitHub token with actions:write permission",
    )
    args = parser.parse_args()

    if not args.repository:
        raise ValueError("Missing GitHub repository. Pass --repository or set GITHUB_REPOSITORY.")
    if not args.token:
        raise ValueError("Missing GitHub token. Pass --token or set GITHUB_TOKEN.")

    owner, repo = parse_repository(args.repository)
    dispatch_workflow(
        owner=owner,
        repo=repo,
        workflow=args.workflow,
        ref=args.ref,
        token=args.token,
        inputs={"tag_name": args.tag},
    )
    print(f"Dispatched {args.workflow} for {args.tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
