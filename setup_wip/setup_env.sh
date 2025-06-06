#!/bin/bash

# Default virtual env directory
VENV_DIR="venv"

# Check if a virtual env directory argument is passed
if [ ! -z "$1" ]; then
  VENV_DIR="$1"
fi

echo "Creating virtual environment in $VENV_DIR..."

# Create virtual environment
python3 -m venv "$VENV_DIR"

echo "Activating virtual environment..."
# Activate virtual environment (works for bash/zsh)
source "$VENV_DIR/bin/activate"

echo "Installing packages from requirements.txt..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Done. To activate the virtual environment, run:"
echo "source $VENV_DIR/bin/activate"
