"""Data models for activity metrics."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class UserStats:
    """Statistics for a single user."""

    username: str
    issues_opened: int = 0
    issues_closed: int = 0
    prs_opened: int = 0
    prs_closed: int = 0
    prs_merged: int = 0
    commits: int = 0
    pr_comments: int = 0
    issue_comments: int = 0


@dataclass
class RepoStats:
    """Statistics for a single repository."""

    forge: str
    repo: str
    user_stats: dict[str, UserStats] = field(default_factory=dict)

    def add_user_stats(self, stats: UserStats) -> None:
        """Add or merge user statistics."""
        if stats.username in self.user_stats:
            existing = self.user_stats[stats.username]
            existing.issues_opened += stats.issues_opened
            existing.issues_closed += stats.issues_closed
            existing.prs_opened += stats.prs_opened
            existing.prs_closed += stats.prs_closed
            existing.prs_merged += stats.prs_merged
            existing.commits += stats.commits
            existing.pr_comments += stats.pr_comments
            existing.issue_comments += stats.issue_comments
        else:
            self.user_stats[stats.username] = stats


@dataclass
class Report:
    """Complete activity report."""

    year: int
    start_date: datetime
    end_date: datetime
    repos: list[RepoStats] = field(default_factory=list)

    def get_total_stats(self) -> dict[str, UserStats]:
        """Aggregate statistics across all repositories."""
        total_stats = {}
        for repo in self.repos:
            for username, stats in repo.user_stats.items():
                if username not in total_stats:
                    total_stats[username] = UserStats(username=username)

                total = total_stats[username]
                total.issues_opened += stats.issues_opened
                total.issues_closed += stats.issues_closed
                total.prs_opened += stats.prs_opened
                total.prs_closed += stats.prs_closed
                total.prs_merged += stats.prs_merged
                total.commits += stats.commits
                total.pr_comments += stats.pr_comments
                total.issue_comments += stats.issue_comments

        return total_stats
