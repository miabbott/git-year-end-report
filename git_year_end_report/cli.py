"""Command-line interface for git-year-end-report."""

from datetime import datetime, timezone
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .config import load_config
from .forges.github import GitHubClient
from .forges.gitlab import GitLabClient
from .forges.pagure import PagureClient
from .models import Report
from .report import generate_markdown_report

app = typer.Typer(help="Generate year-end activity reports from git forges")
console = Console()


def main():
    """Entry point for the CLI application."""
    app()


@app.command()
def generate(
    config_file: Path = typer.Option(
        "config.yaml",
        "--config",
        "-c",
        help="Path to configuration file",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    output: Path = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path (overrides config file setting)",
    ),
    forges: list[str] = typer.Option(
        None,
        "--forge",
        "-f",
        help="Only fetch from specified forge(s). Can be used multiple times. Example: -f github -f gitlab",
    ),
):
    """Generate a year-end activity report from configured git forges.

    This command reads the configuration file, fetches statistics from all
    configured git forges, and generates a comprehensive Markdown report.
    """
    try:
        config = load_config(config_file)
    except Exception as e:
        console.print(f"[red]Error loading configuration:[/red] {e}")
        raise typer.Exit(1)

    # Filter forges if specified on command line
    if forges:
        forge_names_lower = [f.lower() for f in forges]
        filtered_forges = [
            fc for fc in config.forges if fc.name.lower() in forge_names_lower
        ]
        if not filtered_forges:
            console.print(
                f"[red]Error: None of the specified forges ({', '.join(forges)}) "
                f"are configured in {config_file}[/red]"
            )
            raise typer.Exit(1)
        config.forges = filtered_forges
        console.print(
            f"[yellow]Filtering to forges: {', '.join(fc.name for fc in config.forges)}[/yellow]\n"
        )

    start_date = datetime(config.year, 1, 1, tzinfo=timezone.utc)
    end_date = datetime.now(timezone.utc)

    if end_date.year != config.year:
        end_date = datetime(config.year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

    report = Report(year=config.year, start_date=start_date, end_date=end_date)

    output_path = output or config.output or f"report-{config.year}.md"

    console.print(f"[bold blue]Git Year-End Report Generator[/bold blue]")
    console.print(f"Year: {config.year}")
    console.print(f"Period: {start_date.date()} to {end_date.date()}")
    console.print(f"Output: {output_path}\n")

    forge_clients = {
        "github": GitHubClient,
        "gitlab": GitLabClient,
        "pagure": PagureClient,
    }

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for forge_config in config.forges:
            forge_name = forge_config.name.lower()

            if forge_name not in forge_clients:
                console.print(
                    f"[yellow]Warning: Unknown forge '{forge_name}', skipping[/yellow]"
                )
                continue

            client_class = forge_clients[forge_name]
            endpoint = forge_config.endpoint

            if endpoint:
                client = client_class(token=forge_config.token, endpoint=endpoint)
            else:
                client = client_class(token=forge_config.token)

            for repo in forge_config.repos:
                task = progress.add_task(
                    f"Fetching stats for {forge_config.name}/{repo}...", total=None
                )

                try:
                    repo_stats = client.get_repo_stats(
                        repo, forge_config.usernames, start_date, end_date
                    )
                    report.repos.append(repo_stats)
                    progress.update(
                        task,
                        description=f"[green][/green] {forge_config.name}/{repo}",
                    )
                except Exception as e:
                    progress.update(
                        task,
                        description=f"[red][/red] {forge_config.name}/{repo}: {e}",
                    )
                    console.print(
                        f"[red]Error fetching stats for {forge_config.name}/{repo}:[/red] {e}"
                    )

                progress.remove_task(task)

    console.print("\n[bold green]Generating report...[/bold green]")

    try:
        generate_markdown_report(report, output_path)
        console.print(f"\n[bold green][/bold green] Report generated: {output_path}")
    except Exception as e:
        console.print(f"[red]Error generating report:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def validate(
    config_file: Path = typer.Option(
        "config.yaml",
        "--config",
        "-c",
        help="Path to configuration file",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
):
    """Validate the configuration file without generating a report.

    This command checks that the configuration file is properly formatted
    and contains all required fields.
    """
    try:
        config = load_config(config_file)
        console.print("[green][/green] Configuration is valid")
        console.print(f"\nYear: {config.year}")
        console.print(f"Forges configured: {len(config.forges)}")

        for forge_config in config.forges:
            console.print(f"\n  {forge_config.name}:")
            console.print(f"    Repositories: {len(forge_config.repos)}")
            console.print(f"    Usernames: {len(forge_config.usernames)}")
            console.print(f"    Token: {'' if forge_config.token else ''}")

    except Exception as e:
        console.print(f"[red] Configuration is invalid:[/red] {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    main()

@app.command()
def enumerate(
    config_file: Path = typer.Option(
        "config.yaml",
        "--config",
        "-c",
        help="Path to configuration file",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    forges: list[str] = typer.Option(
        None,
        "--forge",
        "-f",
        help="Only enumerate from specified forge(s). Can be used multiple times.",
    ),
):
    """Enumerate repositories where configured users have been active.

    This command discovers all repositories where the configured users have
    filed issues, created pull requests, or made comments. The output is
    formatted as YAML that can be directly inserted into the config file.
    """
    try:
        config = load_config(config_file)
    except Exception as e:
        console.print(f"[red]Error loading configuration:[/red] {e}")
        raise typer.Exit(1)

    # Filter forges if specified on command line
    if forges:
        forge_names_lower = [f.lower() for f in forges]
        filtered_forges = [
            fc for fc in config.forges if fc.name.lower() in forge_names_lower
        ]
        if not filtered_forges:
            console.print(
                f"[red]Error: None of the specified forges ({', '.join(forges)}) "
                f"are configured in {config_file}[/red]"
            )
            raise typer.Exit(1)
        config.forges = filtered_forges

    start_date = datetime(config.year, 1, 1, tzinfo=timezone.utc)
    end_date = datetime.now(timezone.utc)

    if end_date.year != config.year:
        end_date = datetime(config.year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

    console.print(f"\n[bold blue]Repository Enumeration[/bold blue]")
    console.print(f"Year: {config.year}")
    console.print(f"Period: {start_date.date()} to {end_date.date()}\n")

    forge_clients = {
        "github": GitHubClient,
        "gitlab": GitLabClient,
        "pagure": PagureClient,
    }

    results = {}

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for forge_config in config.forges:
            forge_name = forge_config.name.lower()

            if forge_name not in forge_clients:
                console.print(
                    f"[yellow]Warning: Unknown forge '{forge_name}', skipping[/yellow]"
                )
                continue

            client_class = forge_clients[forge_name]
            endpoint = forge_config.endpoint

            if endpoint:
                client = client_class(token=forge_config.token, endpoint=endpoint)
            else:
                client = client_class(token=forge_config.token)

            task = progress.add_task(
                f"Enumerating repos for {forge_config.name}...", total=None
            )

            try:
                repos = client.enumerate_repos(
                    forge_config.usernames, start_date, end_date
                )
                results[forge_config.name] = sorted(repos)
                progress.update(
                    task,
                    description=f"[green]Found {len(repos)} repos for {forge_config.name}[/green]",
                )
            except Exception as e:
                progress.update(
                    task,
                    description=f"[red]Error for {forge_config.name}: {e}[/red]",
                )
                console.print(
                    f"[red]Error enumerating {forge_config.name}:[/red] {e}"
                )

            progress.remove_task(task)

    # Output YAML-formatted results
    console.print("\n[bold green]Discovered Repositories[/bold green]\n")
    console.print("Copy this into your config.yaml file:\n")
    console.print("```yaml")
    console.print("forges:")

    for forge_name, repos in results.items():
        if repos:
            console.print(f"  {forge_name.lower()}:")
            console.print(f"    token: ${{{forge_name.upper()}_TOKEN}}")
            console.print("    usernames:")
            # Get usernames from config
            forge_config = next(
                (fc for fc in config.forges if fc.name.lower() == forge_name.lower()),
                None,
            )
            if forge_config:
                for username in forge_config.usernames:
                    console.print(f"      - {username}")
            console.print("    repos:")
            for repo in repos:
                console.print(f"      - {repo}")
            console.print()

    console.print("```")

