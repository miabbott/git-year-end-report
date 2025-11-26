"""GitLab API client implementation."""

from datetime import datetime
from urllib.parse import quote

import httpx

from ..forge_client import ForgeClient
from ..models import RepoStats, UserStats


class GitLabClient(ForgeClient):
    """GitLab API client for fetching repository statistics."""

    def __init__(
        self, token: str | None = None, endpoint: str = "https://gitlab.com/api/v4"
    ):
        """Initialize GitLab client.

        Args:
            token: GitLab personal access token
            endpoint: API endpoint URL (for self-hosted GitLab)
        """
        super().__init__(token)
        self.endpoint = endpoint.rstrip("/")
        self.headers = {}
        if self.token:
            self.headers["PRIVATE-TOKEN"] = self.token

    def get_forge_name(self) -> str:
        """Return the forge name."""
        return "GitLab"

    def get_repo_stats(
        self,
        repo: str,
        usernames: list[str],
        start_date: datetime,
        end_date: datetime,
    ) -> RepoStats:
        """Fetch statistics for a GitLab repository.

        Args:
            repo: Repository in format "group/project"
            usernames: List of GitLab usernames to track
            start_date: Start of date range
            end_date: End of date range

        Returns:
            RepoStats object with all statistics
        """
        repo_stats = RepoStats(forge="GitLab", repo=repo)
        project_id = quote(repo, safe="")

        for username in usernames:
            user_stats = UserStats(username=username)

            user_stats.issues_opened = self._count_issues(
                project_id, username, start_date, end_date, created=True
            )
            user_stats.issues_closed = self._count_issues(
                project_id, username, start_date, end_date, created=False
            )
            user_stats.prs_opened = self._count_merge_requests(
                project_id, username, start_date, end_date, created=True
            )
            user_stats.prs_closed = self._count_merge_requests(
                project_id, username, start_date, end_date, created=False
            )
            user_stats.prs_merged = self._count_merged_merge_requests(
                project_id, username, start_date, end_date
            )
            user_stats.commits = self._count_commits(
                project_id, username, start_date, end_date
            )
            user_stats.pr_comments = self._count_mr_comments(
                project_id, username, start_date, end_date
            )
            user_stats.issue_comments = self._count_issue_comments(
                project_id, username, start_date, end_date
            )

            repo_stats.add_user_stats(user_stats)

        return repo_stats

    def _make_request(self, url: str, params: dict | None = None) -> list[dict]:
        """Make paginated requests to GitLab API.

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
            page = 1
            while True:
                params["page"] = page
                response = client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                if not data:
                    break

                if isinstance(data, list):
                    results.extend(data)
                else:
                    results.append(data)
                    break

                total_pages = response.headers.get("X-Total-Pages")
                if total_pages and page >= int(total_pages):
                    break

                page += 1

        return results

    def _count_issues(
        self,
        project_id: str,
        username: str,
        start_date: datetime,
        end_date: datetime,
        created: bool,
    ) -> int:
        """Count issues for a user in a date range.

        Args:
            project_id: URL-encoded project ID
            username: GitLab username
            start_date: Start of date range
            end_date: End of date range
            created: If True, count created issues; if False, count closed issues

        Returns:
            Number of issues
        """
        url = f"{self.endpoint}/projects/{project_id}/issues"
        params = {
            "author_username": username if created else None,
            "created_after": start_date.isoformat() if created else None,
            "created_before": end_date.isoformat() if created else None,
        }
        params = {k: v for k, v in params.items() if v is not None}

        issues = self._make_request(url, params)

        if not created:
            issues = [
                i
                for i in issues
                if i.get("closed_at")
                and start_date
                <= datetime.fromisoformat(i["closed_at"].replace("Z", "+00:00"))
                <= end_date
            ]

        return len(issues)

    def _count_merge_requests(
        self,
        project_id: str,
        username: str,
        start_date: datetime,
        end_date: datetime,
        created: bool,
    ) -> int:
        """Count merge requests for a user in a date range.

        Args:
            project_id: URL-encoded project ID
            username: GitLab username
            start_date: Start of date range
            end_date: End of date range
            created: If True, count created MRs; if False, count closed MRs

        Returns:
            Number of merge requests
        """
        url = f"{self.endpoint}/projects/{project_id}/merge_requests"
        params = {
            "author_username": username if created else None,
            "created_after": start_date.isoformat() if created else None,
            "created_before": end_date.isoformat() if created else None,
            "state": "all",
        }
        params = {k: v for k, v in params.items() if v is not None}

        mrs = self._make_request(url, params)

        if not created:
            mrs = [
                mr
                for mr in mrs
                if mr.get("closed_at")
                and start_date
                <= datetime.fromisoformat(mr["closed_at"].replace("Z", "+00:00"))
                <= end_date
            ]

        return len(mrs)

    def _count_merged_merge_requests(
        self, project_id: str, username: str, start_date: datetime, end_date: datetime
    ) -> int:
        """Count merged merge requests for a user in a date range.

        Args:
            project_id: URL-encoded project ID
            username: GitLab username
            start_date: Start of date range
            end_date: End of date range

        Returns:
            Number of merged merge requests
        """
        url = f"{self.endpoint}/projects/{project_id}/merge_requests"
        params = {
            "author_username": username,
            "state": "merged",
        }

        mrs = self._make_request(url, params)
        merged_mrs = [
            mr
            for mr in mrs
            if mr.get("merged_at")
            and start_date
            <= datetime.fromisoformat(mr["merged_at"].replace("Z", "+00:00"))
            <= end_date
        ]

        return len(merged_mrs)

    def _count_commits(
        self, project_id: str, username: str, start_date: datetime, end_date: datetime
    ) -> int:
        """Count commits for a user in a date range.

        Args:
            project_id: URL-encoded project ID
            username: GitLab username
            start_date: Start of date range
            end_date: End of date range

        Returns:
            Number of commits
        """
        url = f"{self.endpoint}/projects/{project_id}/repository/commits"
        params = {
            "author": username,
            "since": start_date.isoformat(),
            "until": end_date.isoformat(),
        }

        commits = self._make_request(url, params)
        return len(commits)

    def _count_mr_comments(
        self, project_id: str, username: str, start_date: datetime, end_date: datetime
    ) -> int:
        """Count merge request comments for a user in a date range.

        Args:
            project_id: URL-encoded project ID
            username: GitLab username
            start_date: Start of date range
            end_date: End of date range

        Returns:
            Number of MR comments
        """
        url = f"{self.endpoint}/projects/{project_id}/merge_requests"
        mrs = self._make_request(url, {"state": "all"})

        comment_count = 0
        for mr in mrs:
            notes_url = f"{self.endpoint}/projects/{project_id}/merge_requests/{mr['iid']}/notes"
            notes = self._make_request(notes_url)

            user_notes = [
                n
                for n in notes
                if n["author"]["username"] == username
                and not n.get("system", False)
                and start_date
                <= datetime.fromisoformat(n["created_at"].replace("Z", "+00:00"))
                <= end_date
            ]
            comment_count += len(user_notes)

        return comment_count

    def _count_issue_comments(
        self, project_id: str, username: str, start_date: datetime, end_date: datetime
    ) -> int:
        """Count issue comments for a user in a date range.

        Args:
            project_id: URL-encoded project ID
            username: GitLab username
            start_date: Start of date range
            end_date: End of date range

        Returns:
            Number of issue comments
        """
        url = f"{self.endpoint}/projects/{project_id}/issues"
        issues = self._make_request(url, {"state": "all"})

        comment_count = 0
        for issue in issues:
            notes_url = (
                f"{self.endpoint}/projects/{project_id}/issues/{issue['iid']}/notes"
            )
            notes = self._make_request(notes_url)

            user_notes = [
                n
                for n in notes
                if n["author"]["username"] == username
                and not n.get("system", False)
                and start_date
                <= datetime.fromisoformat(n["created_at"].replace("Z", "+00:00"))
                <= end_date
            ]
            comment_count += len(user_notes)

        return comment_count
