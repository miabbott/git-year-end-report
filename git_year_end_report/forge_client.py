"""Base class for git forge API clients."""

from abc import ABC, abstractmethod
from datetime import datetime

from .models import RepoStats


class ForgeClient(ABC):
    """Abstract base class for git forge API clients.

    This class defines the interface that all forge-specific clients must
    implement, making it easy to add support for new git forges.
    """

    def __init__(self, token: str | None = None):
        """Initialize the forge client.

        Args:
            token: API token for authentication (optional)
        """
        self.token = token

    @abstractmethod
    def get_repo_stats(
        self,
        repo: str,
        usernames: list[str],
        start_date: datetime,
        end_date: datetime,
    ) -> RepoStats:
        """Fetch statistics for a repository.

        Args:
            repo: Repository identifier (e.g., "owner/repo")
            usernames: List of usernames to track
            start_date: Start of date range
            end_date: End of date range

        Returns:
            RepoStats object containing all user statistics for the repo
        """
        pass

    @abstractmethod
    def get_forge_name(self) -> str:
        """Return the name of this forge (e.g., 'GitHub', 'GitLab').

        Returns:
            Human-readable name of the forge
        """
        pass
