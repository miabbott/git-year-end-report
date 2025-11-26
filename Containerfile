# Multi-stage build for git-year-end-report

# Build stage
FROM python:3.13-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock ./
COPY git_year_end_report ./git_year_end_report

# Install dependencies
RUN uv sync --frozen --no-dev

# Runtime stage
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY git_year_end_report ./git_year_end_report

# Set PATH to use virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Create directory for config and output
RUN mkdir -p /data

# Set working directory to data mount point
WORKDIR /data

# Run the CLI
ENTRYPOINT ["python", "-m", "git_year_end_report.cli"]
CMD ["--help"]
