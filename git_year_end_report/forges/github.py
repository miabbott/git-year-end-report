"""GitHub API client implementation."""

from datetime import datetime

import httpx

from ..forge_client import ForgeClient
from ..models import RepoStats, UserStats


class GitHubClient(ForgeClient):
    """GitHub API client for fetching repository statistics."""

    def __init__(self, token: str | None = None, endpoint: str = "https://api.github.com"):
        """Initialize GitHub client.

        Args:
            token: GitHub personal access token
            endpoint: API endpoint URL (for GitHub Enterprise)
        """
        super().__init__(token)
        self.endpoint = endpoint.rstrip("/")
        self.headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"

    def get_forge_name(self) -> str:
        """Return the forge name."""
        return "GitHub"

    def get_repo_stats(
        self,
        repo: str,
        usernames: list[str],
        start_date: datetime,
        end_date: datetime,
    ) -> RepoStats:
        """Fetch statistics for a GitHub repository.

        Args:
            repo: Repository in format "owner/repo"
            usernames: List of GitHub usernames to track
            start_date: Start of date range
            end_date: End of date range

        Returns:
            RepoStats object with all statistics
        """
        repo_stats = RepoStats(forge="GitHub", repo=repo)

        for username in usernames:
            user_stats = UserStats(username=username)

            user_stats.issues_opened = self._count_issues(
                repo, username, start_date, end_date, state="open", created=True
            )
            user_stats.issues_closed = self._count_issues(
                repo, username, start_date, end_date, state="closed", created=False
            )
            user_stats.prs_opened = self._count_pull_requests(
                repo, username, start_date, end_date, state="open", created=True
            )
            user_stats.prs_closed = self._count_pull_requests(
                repo, username, start_date, end_date, state="closed", created=False
            )
            user_stats.prs_merged = self._count_merged_pull_requests(
                repo, username, start_date, end_date
            )
            user_stats.commits = self._count_commits(repo, username, start_date, end_date)
            user_stats.pr_comments = self._count_pr_comments(
                repo, username, start_date, end_date
            )
            user_stats.issue_comments = self._count_issue_comments(
                repo, username, start_date, end_date
            )

            repo_stats.add_user_stats(user_stats)

        return repo_stats

    def _make_request(self, url: str, params: dict | None = None) -> list[dict]:
        """Make paginated requests to GitHub API.

        Args:
            url: API endpoint URL
            params: Query parameters

        Returns:
            List of all results from paginated responses
        """
        results = []
        params = params or {}
        params["per_page"] = 100

        with httpx.Client(headers=self.headers, timeout=30.0) as client:
            while url:
                response = client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                if isinstance(data, list):
                    results.extend(data)
                else:
                    results.append(data)

                link_header = response.headers.get("Link", "")
                url = self._get_next_page_url(link_header)
                params = None

        return results

    def _get_next_page_url(self, link_header: str) -> str | None:
        """Extract next page URL from Link header.

        Args:
            link_header: GitHub Link header value

        Returns:
            URL of next page or None if no more pages
        """
        if not link_header:
            return None

        for link in link_header.split(","):
            parts = link.split(";")
            if len(parts) == 2 and 'rel="next"' in parts[1]:
                return parts[0].strip("<> ")

        return None

    def _count_issues(
        self,
        repo: str,
        username: str,
        start_date: datetime,
        end_date: datetime,
        state: str,
        created: bool,
    ) -> int:
        """Count issues for a user in a date range.

        Args:
            repo: Repository in format "owner/repo"
            username: GitHub username
            start_date: Start of date range
            end_date: End of date range
            state: Issue state ("open" or "closed")
            created: If True, count created issues; if False, count closed issues

        Returns:
            Number of issues
        """
        url = f"{self.endpoint}/repos/{repo}/issues"
        params = {
            "creator": username if created else None,
            "state": state if not created else "all",
            "since": start_date.isoformat(),
        }
        params = {k: v for k, v in params.items() if v is not None}

        issues = self._make_request(url, params)
        issues = [i for i in issues if "pull_request" not in i]

        if created:
            issues = [
                i
                for i in issues
                if start_date <= datetime.fromisoformat(i["created_at"].replace("Z", "+00:00")) <= end_date
            ]
        else:
            issues = [
                i
                for i in issues
                if i.get("closed_at")
                and start_date <= datetime.fromisoformat(i["closed_at"].replace("Z", "+00:00")) <= end_date
            ]

        return len(issues)

    def _count_pull_requests(
        self,
        repo: str,
        username: str,
        start_date: datetime,
        end_date: datetime,
        state: str,
        created: bool,
    ) -> int:
        """Count pull requests for a user in a date range.

        Args:
            repo: Repository in format "owner/repo"
            username: GitHub username
            start_date: Start of date range
            end_date: End of date range
            state: PR state ("open" or "closed")
            created: If True, count created PRs; if False, count closed PRs

        Returns:
            Number of pull requests
        """
        url = f"{self.endpoint}/repos/{repo}/pulls"
        params = {
            "creator": username if created else None,
            "state": state if not created else "all",
        }
        params = {k: v for k, v in params.items() if v is not None}

        prs = self._make_request(url, params)

        if created:
            prs = [
                pr
                for pr in prs
                if start_date <= datetime.fromisoformat(pr["created_at"].replace("Z", "+00:00")) <= end_date
            ]
        else:
            prs = [
                pr
                for pr in prs
                if pr.get("closed_at")
                and start_date <= datetime.fromisoformat(pr["closed_at"].replace("Z", "+00:00")) <= end_date
            ]

        return len(prs)

    def _count_merged_pull_requests(
        self, repo: str, username: str, start_date: datetime, end_date: datetime
    ) -> int:
        """Count merged pull requests for a user in a date range.

        Args:
            repo: Repository in format "owner/repo"
            username: GitHub username
            start_date: Start of date range
            end_date: End of date range

        Returns:
            Number of merged pull requests
        """
        url = f"{self.endpoint}/repos/{repo}/pulls"
        params = {"creator": username, "state": "closed"}

        prs = self._make_request(url, params)
        merged_prs = [
            pr
            for pr in prs
            if pr.get("merged_at")
            and start_date <= datetime.fromisoformat(pr["merged_at"].replace("Z", "+00:00")) <= end_date
        ]

        return len(merged_prs)

    def _count_commits(
        self, repo: str, username: str, start_date: datetime, end_date: datetime
    ) -> int:
        """Count commits for a user in a date range.

        Args:
            repo: Repository in format "owner/repo"
            username: GitHub username
            start_date: Start of date range
            end_date: End of date range

        Returns:
            Number of commits
        """
        url = f"{self.endpoint}/repos/{repo}/commits"
        params = {
            "author": username,
            "since": start_date.isoformat(),
            "until": end_date.isoformat(),
        }

        commits = self._make_request(url, params)
        return len(commits)

    def _count_pr_comments(
        self, repo: str, username: str, start_date: datetime, end_date: datetime
    ) -> int:
        """Count PR review comments for a user in a date range.

        Args:
            repo: Repository in format "owner/repo"
            username: GitHub username
            start_date: Start of date range
            end_date: End of date range

        Returns:
            Number of PR review comments
        """
        url = f"{self.endpoint}/repos/{repo}/pulls/comments"
        params = {"since": start_date.isoformat()}

        comments = self._make_request(url, params)
        user_comments = [
            c
            for c in comments
            if c["user"]["login"] == username
            and start_date <= datetime.fromisoformat(c["created_at"].replace("Z", "+00:00")) <= end_date
        ]

        return len(user_comments)

    def _count_issue_comments(
        self, repo: str, username: str, start_date: datetime, end_date: datetime
    ) -> int:
        """Count issue comments for a user in a date range.

        Args:
            repo: Repository in format "owner/repo"
            username: GitHub username
            start_date: Start of date range
            end_date: End of date range

        Returns:
            Number of issue comments
        """
        url = f"{self.endpoint}/repos/{repo}/issues/comments"
        params = {"since": start_date.isoformat()}

        comments = self._make_request(url, params)
        user_comments = [
            c
            for c in comments
            if c["user"]["login"] == username
            and start_date <= datetime.fromisoformat(c["created_at"].replace("Z", "+00:00")) <= end_date
        ]

        return len(user_comments)
