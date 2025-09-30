#!/bin/bash

# Script to initialize virtual environment and install dependencies

echo "Creating virtual environment..."
python3 -m venv venv

echo "Activating virtual environment..."
source venv/bin/activate

echo "Upgrading pip..."
pip install --upgrade pip

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Setup complete! To activate the virtual environment, run:"
echo "source venv/bin/activate"
