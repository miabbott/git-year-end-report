"""Configuration management for git-year-end-report."""

import os
import re
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class ForgeConfig:
    """Configuration for a single git forge."""

    name: str
    token: str | None
    endpoint: str | None
    usernames: list[str]
    repos: list[str]


@dataclass
class Config:
    """Main configuration object."""

    year: int
    forges: list[ForgeConfig]
    output: str | None = None


def _expand_env_vars(value: str) -> str:
    """Expand environment variable references in a string.

    Supports ${VAR_NAME} syntax. Returns the original string if the
    environment variable is not set.

    Args:
        value: String potentially containing ${VAR_NAME} references

    Returns:
        String with environment variables expanded
    """
    if not isinstance(value, str):
        return value

    pattern = re.compile(r"\$\{([^}]+)\}")

    def replacer(match):
        var_name = match.group(1)
        return os.environ.get(var_name, match.group(0))

    return pattern.sub(replacer, value)


def _expand_dict(data: dict) -> dict:
    """Recursively expand environment variables in a dictionary.

    Args:
        data: Dictionary with potential environment variable references

    Returns:
        Dictionary with all environment variables expanded
    """
    result = {}
    for key, value in data.items():
        if isinstance(value, dict):
            result[key] = _expand_dict(value)
        elif isinstance(value, list):
            result[key] = [
                _expand_dict(item) if isinstance(item, dict) else _expand_env_vars(str(item)) if isinstance(item, str) else item
                for item in value
            ]
        elif isinstance(value, str):
            result[key] = _expand_env_vars(value)
        else:
            result[key] = value
    return result


def load_config(config_path: str | Path) -> Config:
    """Load and parse configuration from a YAML file.

    Args:
        config_path: Path to the configuration file

    Returns:
        Parsed configuration object

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config is invalid
    """
    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path) as f:
        raw_config = yaml.safe_load(f)

    if not raw_config:
        raise ValueError("Configuration file is empty")

    raw_config = _expand_dict(raw_config)

    if "year" not in raw_config:
        raise ValueError("Configuration must specify a 'year'")

    if "forges" not in raw_config or not raw_config["forges"]:
        raise ValueError("Configuration must specify at least one forge")

    year = raw_config["year"]
    if not isinstance(year, int) or year < 2000 or year > 9999:
        raise ValueError(f"Invalid year: {year}")

    forges = []
    for forge_name, forge_data in raw_config["forges"].items():
        if not isinstance(forge_data, dict):
            raise ValueError(f"Invalid configuration for forge: {forge_name}")

        token = forge_data.get("token")
        endpoint = forge_data.get("endpoint")
        usernames = forge_data.get("usernames", [])
        repos = forge_data.get("repos", [])

        if not usernames:
            raise ValueError(f"Forge {forge_name} must specify at least one username")

        if not repos:
            raise ValueError(f"Forge {forge_name} must specify at least one repository")

        forges.append(
            ForgeConfig(
                name=forge_name,
                token=token,
                endpoint=endpoint,
                usernames=usernames,
                repos=repos,
            )
        )

    output = raw_config.get("output")

    return Config(year=year, forges=forges, output=output)
