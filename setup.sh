#!/bin/bash -e
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install the requirements
pip install -r requirements.txt

# Install additional packages for type checking
mypy --install-types --non-interactive