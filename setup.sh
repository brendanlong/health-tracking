#!/bin/bash -e
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install the requirements
pip install -r requirements.txt

# Install the package in development mode
pip install -e .

# Install additional packages for type checking
mypy --install-types --non-interactive

# Install pre-commit hooks
pre-commit install

echo "Setup complete! You can now use:"
echo "  bin/fitbit-data.py - Fetch Fitbit data"
echo "  bin/sheets-upload.py - Interact with Google Sheets"