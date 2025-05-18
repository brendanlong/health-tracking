#!/bin/bash -e

# Install uv if not already installed
if ! command -v uv &> /dev/null; then
    echo "Please install uv: https://github.com/astral-sh/uv?tab=readme-ov-file#installation"
fi

# Install dependencies and setup venv
uv sync

# Install pre-commit hooks
pre-commit install

echo "Setup complete!"