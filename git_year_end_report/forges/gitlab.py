"""GitLab API client implementation."""

import logging
from datetime import datetime
from urllib.parse import quote

import httpx

from ..forge_client import ForgeClient
from ..models import RepoStats, UserStats

logger = logging.getLogger(__name__)


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
                logger.debug(f"GitLab API: GET {url} (page {page}, params: {params})")
                response = client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                if isinstance(data, list):
                    logger.debug(f"GitLab API: Received {len(data)} items")
                else:
                    logger.debug(f"GitLab API: Received single item response")

                if not data:
                    break

                if isinstance(data, list):
                    results.extend(data)
                else:
                    results.append(data)
                    break

                total_pages = response.headers.get("X-Total-Pages")
                if total_pages and page >= int(total_pages):
                    logger.debug(f"GitLab API: Reached last page ({page}/{total_pages})")
                    break

                page += 1

        logger.debug(f"GitLab API: Total results: {len(results)}")
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
        # Only fetch MRs updated after start_date to reduce API calls
        params = {
            "state": "all",
            "updated_after": start_date.isoformat(),
        }
        mrs = self._make_request(url, params)

        comment_count = 0
        for mr in mrs:
            notes_url = f"{self.endpoint}/projects/{project_id}/merge_requests/{mr['iid']}/notes"
            params_notes = {
                "sort": "asc",
                "order_by": "created_at",
            }
            notes = self._make_request(notes_url, params_notes)

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
        # Only fetch issues updated after start_date to reduce API calls
        params = {
            "state": "all",
            "updated_after": start_date.isoformat(),
        }
        issues = self._make_request(url, params)

        comment_count = 0
        for issue in issues:
            notes_url = (
                f"{self.endpoint}/projects/{project_id}/issues/{issue['iid']}/notes"
            )
            params_notes = {
                "sort": "asc",
                "order_by": "created_at",
            }
            notes = self._make_request(notes_url, params_notes)

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

    def enumerate_repos(
        self,
        usernames: list[str],
        start_date: datetime,
        end_date: datetime,
    ) -> set[str]:
        """Enumerate repositories where users have been active.

        Uses GitLab's API to find projects where the specified users
        have activity.

        Args:
            usernames: List of GitLab usernames to search for
            start_date: Start of date range
            end_date: End of date range

        Returns:
            Set of repository identifiers in "group/project" format
        """
        repos = set()

        for username in usernames:
            # Get user ID first
            user_id = self._get_user_id(username)
            if not user_id:
                continue

            # Get issues created by user
            repos.update(self._get_user_issues(user_id, start_date, end_date))

            # Get merge requests created by user
            repos.update(self._get_user_merge_requests(user_id, start_date, end_date))

        return repos

    def _get_user_id(self, username: str) -> int | None:
        """Get the user ID for a username.

        Args:
            username: GitLab username

        Returns:
            User ID or None if not found
        """
        url = f"{self.endpoint}/users"
        params = {"username": username}

        try:
            users = self._make_request(url, params)
            if users and len(users) > 0:
                return users[0].get("id")
        except Exception:
            pass

        return None

    def _get_user_issues(
        self, user_id: int, start_date: datetime, end_date: datetime
    ) -> set[str]:
        """Get projects where user has created issues.

        Args:
            user_id: GitLab user ID
            start_date: Start of date range
            end_date: End of date range

        Returns:
            Set of project paths
        """
        repos = set()
        url = f"{self.endpoint}/issues"
        params = {
            "author_id": user_id,
            "created_after": start_date.isoformat(),
            "created_before": end_date.isoformat(),
            "scope": "all",
        }

        try:
            issues = self._make_request(url, params)
            for issue in issues:
                # Use web_url to extract project path
                web_url = issue.get("web_url", "")
                if web_url:
                    # Extract project path from URL like https://gitlab.com/group/project/-/issues/123
                    parts = web_url.split("/-/")
                    if len(parts) >= 2:
                        project = parts[0].split("/", 3)[-1]  # Get everything after gitlab.com/
                        repos.add(project)
        except Exception:
            pass

        return repos

    def _get_user_merge_requests(
        self, user_id: int, start_date: datetime, end_date: datetime
    ) -> set[str]:
        """Get projects where user has created merge requests.

        Args:
            user_id: GitLab user ID
            start_date: Start of date range
            end_date: End of date range

        Returns:
            Set of project paths
        """
        repos = set()
        url = f"{self.endpoint}/merge_requests"
        params = {
            "author_id": user_id,
            "created_after": start_date.isoformat(),
            "created_before": end_date.isoformat(),
            "scope": "all",
        }

        try:
            mrs = self._make_request(url, params)
            for mr in mrs:
                # Use web_url to extract project path
                web_url = mr.get("web_url", "")
                if web_url:
                    # Extract project path from URL like https://gitlab.com/group/project/-/merge_requests/123
                    parts = web_url.split("/-/")
                    if len(parts) >= 2:
                        project = parts[0].split("/", 3)[-1]  # Get everything after gitlab.com/
                        repos.add(project)
        except Exception:
            pass

        return repos
