# Git Year-End Report

Generate comprehensive year-end activity reports from multiple git forges including GitHub, GitLab, and Pagure.

## Features

- **Multi-forge support**: Collect statistics from GitHub, GitLab, and Pagure
- **Extensible architecture**: Easy to add support for new git forges
- **Comprehensive metrics**: Track issues, pull requests, commits, and comments
- **Flexible configuration**: YAML-based config with environment variable support
- **Beautiful reports**: Generate well-formatted Markdown reports
- **Container support**: Run via Podman or Docker without installing dependencies

## Installation

### Using uv (recommended)

```bash
git clone https://github.com/miabbott/git-year-end-report.git
cd git-year-end-report
uv sync
```

### Using pip

```bash
git clone https://github.com/miabbott/git-year-end-report.git
cd git-year-end-report
pip install -e .
```

### Using containers

```bash
# Build the container image
podman build -t git-year-end-report .

# Or with Docker
docker build -t git-year-end-report .
```

## Configuration

Create a `config.yaml` file based on the provided `config.example.yaml`:

```yaml
year: 2025

forges:
  github:
    token: ${GITHUB_TOKEN}
    usernames:
      - user1
      - user2
    repos:
      - owner/repo1
      - owner/repo2

  gitlab:
    token: ${GITLAB_TOKEN}
    usernames:
      - user3
    repos:
      - group/project

  pagure:
    token: ${PAGURE_TOKEN}
    usernames:
      - user4
    repos:
      - project-name
```

### Authentication Tokens

The tool requires read-only API tokens for each forge:

#### GitHub

Create a personal access token at https://github.com/settings/tokens with these scopes:
- `repo` (for private repositories)
- `public_repo` (for public repositories only)

#### GitLab

Create a personal access token at https://gitlab.com/-/profile/personal_access_tokens with these scopes:
- `read_api`

#### Pagure

Create an API token at https://pagure.io/settings#api-keys with these ACLs:
- `Read access to project information and metadata`

### Environment Variables

Store tokens securely using environment variables:

```bash
export GITHUB_TOKEN="your-github-token"
export GITLAB_TOKEN="your-gitlab-token"
export PAGURE_TOKEN="your-pagure-token"
```

## Usage

### After Installing with uv or pip

Once installed, you can use the `git-year-end-report` command:

```bash
# Generate a report
git-year-end-report generate --config config.yaml

# Validate configuration without generating a report
git-year-end-report validate --config config.yaml

# Specify custom output path
git-year-end-report generate --config config.yaml --output my-report.md
```

### Running from Repository without Installation

If you haven't installed the package, you can run it using `uv run`:

```bash
# Generate a report
uv run git-year-end-report generate --config config.yaml

# Validate configuration
uv run git-year-end-report validate --config config.yaml
```

Or run it as a Python module:

```bash
# Activate the virtual environment first
source .venv/bin/activate

# Then run as a module
python -m git_year_end_report.cli generate --config config.yaml

# Or use the script directly from the venv
.venv/bin/git-year-end-report generate --config config.yaml
```

### Container Usage

Generate a report using the container:

```bash
podman run --rm \
  -v $(pwd):/data:z \
  -e GITHUB_TOKEN \
  -e GITLAB_TOKEN \
  -e PAGURE_TOKEN \
  git-year-end-report generate
```

Validate configuration:

```bash
podman run --rm \
  -v $(pwd):/data:z \
  -e GITHUB_TOKEN \
  -e GITLAB_TOKEN \
  -e PAGURE_TOKEN \
  git-year-end-report validate
```

## Report Output

The generated Markdown report includes:

- **Overall Summary**: Total statistics across all users and repositories
- **Per-User Breakdown**: Individual contributions for each tracked user
- **Per-Repository Breakdown**: Activity within each repository

### Metrics Tracked

- Issues opened
- Issues closed
- Pull requests opened
- Pull requests closed
- Pull requests merged
- Commits
- Pull request comments
- Issue comments

## Adding Support for New Forges

The tool is designed to be extensible. To add support for a new forge:

1. Create a new client class in `git_year_end_report/forges/`
2. Inherit from `ForgeClient` base class
3. Implement required methods:
   - `get_forge_name()`: Return the forge name
   - `get_repo_stats()`: Fetch statistics for a repository
4. Register the client in `cli.py`'s `forge_clients` dictionary

See existing implementations for examples.

## Development

### Running Tests

```bash
uv run pytest
```

### Code Formatting

```bash
uv run ruff format .
```

### Type Checking

```bash
uv run mypy git_year_end_report
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## Acknowledgments

Built with:
- [Typer](https://typer.tiangolo.com/) for CLI
- [Rich](https://rich.readthedocs.io/) for terminal formatting
- [httpx](https://www.python-httpx.org/) for HTTP requests
- [uv](https://github.com/astral-sh/uv) for dependency management
