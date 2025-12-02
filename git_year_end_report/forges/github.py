"""GitHub API client implementation."""

import logging
from datetime import datetime

import httpx

from ..forge_client import ForgeClient
from ..models import RepoStats, UserStats

logger = logging.getLogger(__name__)


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
            page_num = 1
            while url:
                logger.debug(f"GitHub API: GET {url} (page {page_num}, params: {params})")
                response = client.get(url, params=params)
                self.api_call_count += 1
                response.raise_for_status()
                data = response.json()

                if isinstance(data, list):
                    logger.debug(f"GitHub API: Received {len(data)} items")
                    results.extend(data)
                else:
                    logger.debug(f"GitHub API: Received single item response")
                    results.append(data)

                link_header = response.headers.get("Link", "")
                url = self._get_next_page_url(link_header)
                params = None
                page_num += 1

        logger.debug(f"GitHub API: Total results: {len(results)}")
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

        Uses GitHub Search API to fetch user's issues with date filtering,
        then filters to target repository.

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
        url = f"{self.endpoint}/search/issues"

        date_range = f"{start_date.date().isoformat()}..{end_date.date().isoformat()}"
        date_qualifier = "created" if created else "closed"

        # Build search query: author, repo, type, date range, and optionally state
        query_parts = [
            f"author:{username}",
            f"repo:{repo}",
            "type:issue",
            f"{date_qualifier}:{date_range}",
        ]

        if not created:
            query_parts.append(f"state:{state}")

        query = " ".join(query_parts)
        params = {"q": query, "per_page": 100}

        try:
            response = self._make_request(url, params)
            # Search API returns {"items": [...]} format
            items = response[0].get("items", []) if response else []
            return len(items)
        except Exception:
            return 0

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

        Uses GitHub Search API to fetch user's PRs with date filtering,
        then filters to target repository.

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
        url = f"{self.endpoint}/search/issues"

        date_range = f"{start_date.date().isoformat()}..{end_date.date().isoformat()}"
        date_qualifier = "created" if created else "closed"

        # Build search query: author, repo, type, date range, and optionally state
        query_parts = [
            f"author:{username}",
            f"repo:{repo}",
            "type:pr",
            f"{date_qualifier}:{date_range}",
        ]

        if not created:
            query_parts.append(f"state:{state}")

        query = " ".join(query_parts)
        params = {"q": query, "per_page": 100}

        try:
            response = self._make_request(url, params)
            # Search API returns {"items": [...]} format
            items = response[0].get("items", []) if response else []
            return len(items)
        except Exception:
            return 0

    def _count_merged_pull_requests(
        self, repo: str, username: str, start_date: datetime, end_date: datetime
    ) -> int:
        """Count merged pull requests for a user in a date range.

        Uses GitHub Search API to fetch user's merged PRs with date filtering.

        Args:
            repo: Repository in format "owner/repo"
            username: GitHub username
            start_date: Start of date range
            end_date: End of date range

        Returns:
            Number of merged pull requests
        """
        url = f"{self.endpoint}/search/issues"

        date_range = f"{start_date.date().isoformat()}..{end_date.date().isoformat()}"

        # Build search query: author, repo, type, merged state, and merged date
        query = f"author:{username} repo:{repo} type:pr is:merged merged:{date_range}"
        params = {"q": query, "per_page": 100}

        try:
            response = self._make_request(url, params)
            # Search API returns {"items": [...]} format
            items = response[0].get("items", []) if response else []
            return len(items)
        except Exception:
            return 0

    def _count_commits(
        self, repo: str, username: str, start_date: datetime, end_date: datetime
    ) -> int:
        """Count commits for a user in a date range.

        Uses GitHub Search API to fetch user's commits with date filtering.

        Args:
            repo: Repository in format "owner/repo"
            username: GitHub username
            start_date: Start of date range
            end_date: End of date range

        Returns:
            Number of commits
        """
        url = f"{self.endpoint}/search/commits"

        date_range = f"{start_date.date().isoformat()}..{end_date.date().isoformat()}"

        # Build search query: author, repo, and author date
        query = f"author:{username} repo:{repo} author-date:{date_range}"
        params = {"q": query, "per_page": 100}

        try:
            response = self._make_request(url, params)
            # Search API returns {"items": [...]} format
            items = response[0].get("items", []) if response else []
            return len(items)
        except Exception:
            return 0

    def _count_pr_comments(
        self, repo: str, username: str, start_date: datetime, end_date: datetime
    ) -> int:
        """Count PR review comments for a user in a date range.

        Uses GitHub Search API to find PRs where user commented, filtering
        to target repository and date range. This counts the number of PRs
        with comments, not individual comment count.

        Note: GitHub's search API doesn't provide granular comment counting,
        so this approximates activity by counting PRs with user comments.

        Args:
            repo: Repository in format "owner/repo"
            username: GitHub username
            start_date: Start of date range
            end_date: End of date range

        Returns:
            Number of PRs where user commented
        """
        url = f"{self.endpoint}/search/issues"

        date_range = f"{start_date.date().isoformat()}..{end_date.date().isoformat()}"

        # Build search query: commenter, repo, type, and date range
        query = f"commenter:{username} repo:{repo} type:pr updated:{date_range}"
        params = {"q": query, "per_page": 100}

        try:
            response = self._make_request(url, params)
            # Search API returns {"items": [...]} format
            items = response[0].get("items", []) if response else []
            return len(items)
        except Exception:
            return 0

    def _count_issue_comments(
        self, repo: str, username: str, start_date: datetime, end_date: datetime
    ) -> int:
        """Count issue comments for a user in a date range.

        Uses GitHub Search API to find issues where user commented, filtering
        to target repository and date range. This counts the number of issues
        with comments, not individual comment count.

        Note: GitHub's search API doesn't provide granular comment counting,
        so this approximates activity by counting issues with user comments.

        Args:
            repo: Repository in format "owner/repo"
            username: GitHub username
            start_date: Start of date range
            end_date: End of date range

        Returns:
            Number of issues where user commented
        """
        url = f"{self.endpoint}/search/issues"

        date_range = f"{start_date.date().isoformat()}..{end_date.date().isoformat()}"

        # Build search query: commenter, repo, type, and date range
        query = f"commenter:{username} repo:{repo} type:issue updated:{date_range}"
        params = {"q": query, "per_page": 100}

        try:
            response = self._make_request(url, params)
            # Search API returns {"items": [...]} format
            items = response[0].get("items", []) if response else []
            return len(items)
        except Exception:
            return 0

    def enumerate_repos(
        self,
        usernames: list[str],
        start_date: datetime,
        end_date: datetime,
    ) -> set[str]:
        """Enumerate repositories where users have been active.

        Uses GitHub's search API to find repositories where the specified
        users have activity.

        Args:
            usernames: List of GitHub usernames to search for
            start_date: Start of date range
            end_date: End of date range

        Returns:
            Set of repository identifiers in "owner/repo" format
        """
        repos = set()

        for username in usernames:
            # Search for issues created by user
            repos.update(
                self._search_issues(username, start_date, end_date, issue_type="issue")
            )

            # Search for PRs created by user
            repos.update(
                self._search_issues(username, start_date, end_date, issue_type="pr")
            )

            # Search for issue comments by user
            repos.update(self._search_comments(username, start_date, end_date))

        return repos

    def _search_issues(
        self, username: str, start_date: datetime, end_date: datetime, issue_type: str
    ) -> set[str]:
        """Search for issues or PRs created by a user.

        Args:
            username: GitHub username
            start_date: Start of date range
            end_date: End of date range
            issue_type: Either "issue" or "pr"

        Returns:
            Set of repository identifiers
        """
        repos = set()
        url = f"{self.endpoint}/search/issues"

        date_range = f"{start_date.date().isoformat()}..{end_date.date().isoformat()}"
        query = f"author:{username} created:{date_range} type:{issue_type}"

        params = {"q": query, "per_page": 100}

        try:
            response = self._make_request(url, params)
            # Search API returns {"items": [...]} format
            items = response[0].get("items", []) if response else []

            for item in items:
                repo_url = item.get("repository_url", "")
                if repo_url:
                    # Extract owner/repo from URL like https://api.github.com/repos/owner/repo
                    parts = repo_url.split("/repos/")
                    if len(parts) == 2:
                        repos.add(parts[1])

        except Exception:
            # If search fails, skip this username
            pass

        return repos

    def _search_comments(
        self, username: str, start_date: datetime, end_date: datetime
    ) -> set[str]:
        """Search for comments made by a user.

        Args:
            username: GitHub username
            start_date: Start of date range
            end_date: End of date range

        Returns:
            Set of repository identifiers
        """
        repos = set()
        url = f"{self.endpoint}/search/issues"

        date_range = f"{start_date.date().isoformat()}..{end_date.date().isoformat()}"
        query = f"commenter:{username} created:{date_range}"

        params = {"q": query, "per_page": 100}

        try:
            response = self._make_request(url, params)
            # Search API returns {"items": [...]} format
            items = response[0].get("items", []) if response else []

            for item in items:
                repo_url = item.get("repository_url", "")
                if repo_url:
                    # Extract owner/repo from URL
                    parts = repo_url.split("/repos/")
                    if len(parts) == 2:
                        repos.add(parts[1])

        except Exception:
            # If search fails, skip this username
            pass

        return repos
