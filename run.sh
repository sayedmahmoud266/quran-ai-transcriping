#!/bin/bash

# Script to run the application from within the virtual environment

if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Please run setup.sh first."
    exit 1
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Starting the Quran AI API server..."
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
