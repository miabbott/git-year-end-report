"""Pagure API client implementation."""

from datetime import datetime

import httpx

from ..forge_client import ForgeClient
from ..models import RepoStats, UserStats


class PagureClient(ForgeClient):
    """Pagure API client for fetching repository statistics."""

    def __init__(self, token: str | None = None, endpoint: str = "https://pagure.io/api/0"):
        """Initialize Pagure client.

        Args:
            token: Pagure API token
            endpoint: API endpoint URL (for self-hosted Pagure)
        """
        super().__init__(token)
        self.endpoint = endpoint.rstrip("/")
        self.headers = {}
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"

    def get_forge_name(self) -> str:
        """Return the forge name."""
        return "Pagure"

    def get_repo_stats(
        self,
        repo: str,
        usernames: list[str],
        start_date: datetime,
        end_date: datetime,
    ) -> RepoStats:
        """Fetch statistics for a Pagure repository.

        Args:
            repo: Repository name (may include namespace like "fork/user/repo")
            usernames: List of Pagure usernames to track
            start_date: Start of date range
            end_date: End of date range

        Returns:
            RepoStats object with all statistics
        """
        repo_stats = RepoStats(forge="Pagure", repo=repo)

        for username in usernames:
            user_stats = UserStats(username=username)

            user_stats.issues_opened = self._count_issues(
                repo, username, start_date, end_date, created=True
            )
            user_stats.issues_closed = self._count_issues(
                repo, username, start_date, end_date, created=False
            )
            user_stats.prs_opened = self._count_pull_requests(
                repo, username, start_date, end_date, created=True
            )
            user_stats.prs_closed = self._count_pull_requests(
                repo, username, start_date, end_date, created=False
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

    def _make_request(self, url: str, params: dict | None = None) -> dict:
        """Make a request to Pagure API.

        Args:
            url: API endpoint URL
            params: Query parameters

        Returns:
            JSON response as a dictionary
        """
        params = params or {}

        with httpx.Client(headers=self.headers, timeout=30.0) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            return response.json()

    def _count_issues(
        self,
        repo: str,
        username: str,
        start_date: datetime,
        end_date: datetime,
        created: bool,
    ) -> int:
        """Count issues for a user in a date range.

        Args:
            repo: Repository name
            username: Pagure username
            start_date: Start of date range
            end_date: End of date range
            created: If True, count created issues; if False, count closed issues

        Returns:
            Number of issues
        """
        url = f"{self.endpoint}/{repo}/issues"
        params = {
            "status": "all",
            "author": username if created else None,
        }
        params = {k: v for k, v in params.items() if v is not None}

        try:
            data = self._make_request(url, params)
            issues = data.get("issues", [])

            if created:
                issues = [
                    i
                    for i in issues
                    if start_date.timestamp()
                    <= float(i.get("date_created", 0))
                    <= end_date.timestamp()
                ]
            else:
                issues = [
                    i
                    for i in issues
                    if i.get("closed_at")
                    and start_date.timestamp()
                    <= float(i["closed_at"])
                    <= end_date.timestamp()
                ]

            return len(issues)
        except Exception:
            return 0

    def _count_pull_requests(
        self,
        repo: str,
        username: str,
        start_date: datetime,
        end_date: datetime,
        created: bool,
    ) -> int:
        """Count pull requests for a user in a date range.

        Args:
            repo: Repository name
            username: Pagure username
            start_date: Start of date range
            end_date: End of date range
            created: If True, count created PRs; if False, count closed PRs

        Returns:
            Number of pull requests
        """
        url = f"{self.endpoint}/{repo}/pull-requests"
        params = {
            "status": "all",
            "author": username if created else None,
        }
        params = {k: v for k, v in params.items() if v is not None}

        try:
            data = self._make_request(url, params)
            prs = data.get("requests", [])

            if created:
                prs = [
                    pr
                    for pr in prs
                    if start_date.timestamp()
                    <= float(pr.get("date_created", 0))
                    <= end_date.timestamp()
                ]
            else:
                prs = [
                    pr
                    for pr in prs
                    if pr.get("closed_at")
                    and start_date.timestamp()
                    <= float(pr["closed_at"])
                    <= end_date.timestamp()
                ]

            return len(prs)
        except Exception:
            return 0

    def _count_merged_pull_requests(
        self, repo: str, username: str, start_date: datetime, end_date: datetime
    ) -> int:
        """Count merged pull requests for a user in a date range.

        Args:
            repo: Repository name
            username: Pagure username
            start_date: Start of date range
            end_date: End of date range

        Returns:
            Number of merged pull requests
        """
        url = f"{self.endpoint}/{repo}/pull-requests"
        params = {"status": "Merged", "author": username}

        try:
            data = self._make_request(url, params)
            prs = data.get("requests", [])

            merged_prs = [
                pr
                for pr in prs
                if pr.get("date_merged")
                and start_date.timestamp()
                <= float(pr["date_merged"])
                <= end_date.timestamp()
            ]

            return len(merged_prs)
        except Exception:
            return 0

    def _count_commits(
        self, repo: str, username: str, start_date: datetime, end_date: datetime
    ) -> int:
        """Count commits for a user in a date range.

        Args:
            repo: Repository name
            username: Pagure username
            start_date: Start of date range
            end_date: End of date range

        Returns:
            Number of commits
        """
        url = f"{self.endpoint}/{repo}/git/log"
        params = {}

        try:
            data = self._make_request(url, params)
            commits = data.get("commits", [])

            user_commits = [
                c
                for c in commits
                if c.get("author", {}).get("name") == username
                and start_date.timestamp()
                <= float(c.get("commit_time", 0))
                <= end_date.timestamp()
            ]

            return len(user_commits)
        except Exception:
            return 0

    def _count_pr_comments(
        self, repo: str, username: str, start_date: datetime, end_date: datetime
    ) -> int:
        """Count PR comments for a user in a date range.

        Args:
            repo: Repository name
            username: Pagure username
            start_date: Start of date range
            end_date: End of date range

        Returns:
            Number of PR comments
        """
        url = f"{self.endpoint}/{repo}/pull-requests"
        params = {"status": "all"}

        try:
            data = self._make_request(url, params)
            prs = data.get("requests", [])

            comment_count = 0
            for pr in prs:
                pr_url = f"{self.endpoint}/{repo}/pull-request/{pr['id']}"
                pr_data = self._make_request(pr_url)

                comments = pr_data.get("comments", [])
                user_comments = [
                    c
                    for c in comments
                    if c.get("user", {}).get("name") == username
                    and start_date.timestamp()
                    <= float(c.get("date_created", 0))
                    <= end_date.timestamp()
                ]
                comment_count += len(user_comments)

            return comment_count
        except Exception:
            return 0

    def _count_issue_comments(
        self, repo: str, username: str, start_date: datetime, end_date: datetime
    ) -> int:
        """Count issue comments for a user in a date range.

        Args:
            repo: Repository name
            username: Pagure username
            start_date: Start of date range
            end_date: End of date range

        Returns:
            Number of issue comments
        """
        url = f"{self.endpoint}/{repo}/issues"
        params = {"status": "all"}

        try:
            data = self._make_request(url, params)
            issues = data.get("issues", [])

            comment_count = 0
            for issue in issues:
                issue_url = f"{self.endpoint}/{repo}/issue/{issue['id']}"
                issue_data = self._make_request(issue_url)

                comments = issue_data.get("comments", [])
                user_comments = [
                    c
                    for c in comments
                    if c.get("user", {}).get("name") == username
                    and start_date.timestamp()
                    <= float(c.get("date_created", 0))
                    <= end_date.timestamp()
                ]
                comment_count += len(user_comments)

            return comment_count
        except Exception:
            return 0

    def enumerate_repos(
        self,
        usernames: list[str],
        start_date: datetime,
        end_date: datetime,
    ) -> set[str]:
        """Enumerate repositories where users have been active.

        Note: Pagure's API has limited search capabilities, so this
        implementation may not find all repositories where users are active.

        Args:
            usernames: List of Pagure usernames to search for
            start_date: Start of date range
            end_date: End of date range

        Returns:
            Set of repository identifiers
        """
        repos = set()

        for username in usernames:
            # Get user's forked projects
            repos.update(self._get_user_forks(username))

            # Get user's own projects
            repos.update(self._get_user_projects(username))

        return repos

    def _get_user_forks(self, username: str) -> set[str]:
        """Get projects forked by a user.

        Args:
            username: Pagure username

        Returns:
            Set of project names
        """
        repos = set()
        url = f"{self.endpoint}/user/{username}"

        try:
            data = self._make_request(url)
            user_data = data.get("user", {})

            # Get forked repos
            forks = user_data.get("forks", [])
            for fork in forks:
                repo_name = fork.get("fullname", "")
                if repo_name:
                    repos.add(repo_name)

        except Exception:
            pass

        return repos

    def _get_user_projects(self, username: str) -> set[str]:
        """Get projects owned by a user.

        Args:
            username: Pagure username

        Returns:
            Set of project names
        """
        repos = set()
        url = f"{self.endpoint}/user/{username}"

        try:
            data = self._make_request(url)
            user_data = data.get("user", {})

            # Get owned repos
            projects = user_data.get("repos", [])
            for project in projects:
                repo_name = project.get("fullname", "")
                if repo_name:
                    repos.add(repo_name)

        except Exception:
            pass

        return repos
