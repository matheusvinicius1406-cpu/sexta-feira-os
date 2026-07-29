"""GitHub service: issues, PRs, branches, commits, CI status.

Uses the GitHub REST API over stdlib ``urllib`` (no third-party HTTP dependency).
The token is read from ``GITHUB_TOKEN`` and never logged. Writes (create issue,
create PR) require the ``github.write`` capability; **merging is intentionally
not implemented** — it is a critical action that must be performed by a human.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

from ..core.context import ExecutionContext
from ..core.errors import ApprovalRequired, FactoryError, ValidationError

_API = "https://api.github.com"


class GitHubError(FactoryError):
    code = "github_error"


class GitHubService:
    def __init__(self, ctx: ExecutionContext, slug: str | None = None, token: str | None = None) -> None:
        self.ctx = ctx
        self.token = token if token is not None else os.environ.get("GITHUB_TOKEN", "")
        self.slug = slug or self._detect_slug(ctx.factory.config.root)

    # --- repo discovery ----------------------------------------------------
    @staticmethod
    def parse_slug(remote_url: str) -> str | None:
        """Extract ``owner/repo`` from an https or ssh git remote URL."""
        remote_url = remote_url.strip()
        m = re.search(r"github\.com[:/]([^/]+/[^/\s]+?)(?:\.git)?$", remote_url)
        return m.group(1) if m else None

    def _detect_slug(self, root: Path) -> str | None:
        try:
            out = subprocess.run(
                ["git", "-C", str(root), "remote", "get-url", "origin"],
                capture_output=True, text=True, check=False, timeout=10,
            )
            if out.returncode == 0:
                return self.parse_slug(out.stdout)
        except (OSError, subprocess.SubprocessError):
            pass
        return None

    # --- HTTP plumbing -----------------------------------------------------
    def _request(self, method: str, path: str, body: dict | None = None) -> object:
        if not self.slug:
            raise ValidationError("no GitHub repo detected (origin remote missing)")
        url = f"{_API}/repos/{self.slug}{path}"
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("User-Agent", "jarvis-mcp")
        if self.token:
            req.add_header("Authorization", f"Bearer {self.token}")
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:  # noqa: S310 (fixed api host)
                return json.loads(resp.read().decode() or "null")
        except urllib.error.HTTPError as exc:
            raise GitHubError(
                f"GitHub API {exc.code}",
                detail={"status": exc.code, "path": path},
            ) from exc
        except urllib.error.URLError as exc:
            raise GitHubError("GitHub API unreachable", detail={"reason": str(exc.reason)}) from exc

    # --- read --------------------------------------------------------------
    def list_issues(self, state: str = "open", limit: int = 20) -> dict:
        self.ctx.authorize("github.read", "issues")
        data = self._request("GET", f"/issues?state={state}&per_page={min(limit, 100)}")
        items = [
            {"number": i["number"], "title": i["title"], "state": i["state"],
             "is_pr": "pull_request" in i}
            for i in (data or [])
        ]
        return {"repo": self.slug, "count": len(items), "issues": items}

    def get_pull_request(self, number: int) -> dict:
        self.ctx.authorize("github.read", f"pr/{number}")
        pr = self._request("GET", f"/pulls/{number}")
        return {
            "number": pr["number"], "title": pr["title"], "state": pr["state"],
            "draft": pr.get("draft", False), "mergeable": pr.get("mergeable"),
            "head": pr["head"]["ref"], "base": pr["base"]["ref"],
            "additions": pr.get("additions"), "deletions": pr.get("deletions"),
        }

    def ci_status(self, ref: str) -> dict:
        self.ctx.authorize("github.read", f"ci/{ref}")
        data = self._request("GET", f"/commits/{ref}/check-runs")
        runs = [
            {"name": r["name"], "status": r["status"], "conclusion": r.get("conclusion")}
            for r in (data or {}).get("check_runs", [])
        ]
        passed = all(r["conclusion"] in ("success", "neutral", "skipped", None) for r in runs)
        return {"ref": ref, "checks": runs, "all_passed": passed and bool(runs)}

    # --- write (guarded) ---------------------------------------------------
    def create_issue(self, title: str, body: str = "", labels: list[str] | None = None) -> dict:
        self.ctx.authorize("github.write", f"issue:{title}")
        if not title.strip():
            raise ValidationError("issue title must not be empty")
        issue = self._request("POST", "/issues", {"title": title, "body": body, "labels": labels or []})
        self.ctx.log_effect("github.write", target=f"issue#{issue['number']}")
        return {"number": issue["number"], "url": issue["html_url"]}

    def create_pull_request(self, title: str, head: str, base: str = "main", body: str = "") -> dict:
        self.ctx.authorize("github.write", f"pr:{head}->{base}")
        if base in ("main", "master"):
            # PRs *to* main are fine; what's forbidden is auto-merge, below.
            pass
        pr = self._request("POST", "/pulls", {"title": title, "head": head, "base": base, "body": body})
        self.ctx.log_effect("github.write", target=f"pr#{pr['number']}")
        return {"number": pr["number"], "url": pr["html_url"]}

    # --- critical: never automated ----------------------------------------
    def merge_pull_request(self, number: int) -> dict:
        # Deliberately unreachable as an automated action.
        self.ctx.authorize("github.merge", f"pr/{number}")  # not granted to any agent -> denied/approval
        raise ApprovalRequired(
            "merging is a human-only action",
            detail={"pr": number, "how": "review the PR and merge manually or with explicit approval"},
        )
