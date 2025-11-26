"""Markdown report generation."""

from datetime import datetime
from pathlib import Path

from .models import Report, RepoStats, UserStats


def generate_markdown_report(report: Report, output_path: str | Path) -> None:
    """Generate a Markdown report and write it to a file.

    Args:
        report: Report object containing all statistics
        output_path: Path where the report should be written
    """
    output_path = Path(output_path)

    md_content = _build_markdown(report)

    with open(output_path, "w") as f:
        f.write(md_content)


def _build_markdown(report: Report) -> str:
    """Build the complete Markdown content for the report.

    Args:
        report: Report object containing all statistics

    Returns:
        Complete Markdown document as a string
    """
    lines = []

    lines.append(f"# Git Activity Report - {report.year}")
    lines.append("")
    lines.append(
        f"**Report Period:** {report.start_date.strftime('%B %d, %Y')} - "
        f"{report.end_date.strftime('%B %d, %Y')}"
    )
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## Overall Summary")
    lines.append("")
    total_stats = report.get_total_stats()
    lines.extend(_build_summary_table(total_stats))
    lines.append("")

    lines.append("## Per-User Breakdown")
    lines.append("")
    for username in sorted(total_stats.keys()):
        stats = total_stats[username]
        lines.append(f"### {username}")
        lines.append("")
        lines.extend(_build_user_stats_table(stats))
        lines.append("")

    lines.append("## Per-Repository Breakdown")
    lines.append("")
    for repo_stats in report.repos:
        lines.append(f"### {repo_stats.forge} - {repo_stats.repo}")
        lines.append("")
        if repo_stats.user_stats:
            lines.extend(_build_repo_stats_table(repo_stats))
        else:
            lines.append("*No activity found for tracked users.*")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(
        f"*Report generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}*"
    )

    return "\n".join(lines)


def _build_summary_table(total_stats: dict[str, UserStats]) -> list[str]:
    """Build a summary statistics table.

    Args:
        total_stats: Dictionary of username to UserStats

    Returns:
        List of Markdown table lines
    """
    lines = []
    lines.append("| Metric | Total |")
    lines.append("|--------|-------|")

    total_issues_opened = sum(s.issues_opened for s in total_stats.values())
    total_issues_closed = sum(s.issues_closed for s in total_stats.values())
    total_prs_opened = sum(s.prs_opened for s in total_stats.values())
    total_prs_closed = sum(s.prs_closed for s in total_stats.values())
    total_prs_merged = sum(s.prs_merged for s in total_stats.values())
    total_commits = sum(s.commits for s in total_stats.values())
    total_pr_comments = sum(s.pr_comments for s in total_stats.values())
    total_issue_comments = sum(s.issue_comments for s in total_stats.values())

    lines.append(f"| Issues Opened | {total_issues_opened} |")
    lines.append(f"| Issues Closed | {total_issues_closed} |")
    lines.append(f"| PRs Opened | {total_prs_opened} |")
    lines.append(f"| PRs Closed | {total_prs_closed} |")
    lines.append(f"| PRs Merged | {total_prs_merged} |")
    lines.append(f"| Commits | {total_commits} |")
    lines.append(f"| PR Comments | {total_pr_comments} |")
    lines.append(f"| Issue Comments | {total_issue_comments} |")

    return lines


def _build_user_stats_table(stats: UserStats) -> list[str]:
    """Build a statistics table for a single user.

    Args:
        stats: UserStats object

    Returns:
        List of Markdown table lines
    """
    lines = []
    lines.append("| Metric | Count |")
    lines.append("|--------|-------|")
    lines.append(f"| Issues Opened | {stats.issues_opened} |")
    lines.append(f"| Issues Closed | {stats.issues_closed} |")
    lines.append(f"| PRs Opened | {stats.prs_opened} |")
    lines.append(f"| PRs Closed | {stats.prs_closed} |")
    lines.append(f"| PRs Merged | {stats.prs_merged} |")
    lines.append(f"| Commits | {stats.commits} |")
    lines.append(f"| PR Comments | {stats.pr_comments} |")
    lines.append(f"| Issue Comments | {stats.issue_comments} |")

    return lines


def _build_repo_stats_table(repo_stats: RepoStats) -> list[str]:
    """Build a statistics table for a repository.

    Args:
        repo_stats: RepoStats object

    Returns:
        List of Markdown table lines
    """
    lines = []
    lines.append(
        "| User | Issues Opened | Issues Closed | PRs Opened | PRs Closed | "
        "PRs Merged | Commits | PR Comments | Issue Comments |"
    )
    lines.append(
        "|------|---------------|---------------|------------|------------|"
        "------------|---------|-------------|----------------|"
    )

    for username in sorted(repo_stats.user_stats.keys()):
        stats = repo_stats.user_stats[username]
        lines.append(
            f"| {username} | {stats.issues_opened} | {stats.issues_closed} | "
            f"{stats.prs_opened} | {stats.prs_closed} | {stats.prs_merged} | "
            f"{stats.commits} | {stats.pr_comments} | {stats.issue_comments} |"
        )

    return lines
