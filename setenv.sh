#!/bin/bash
# Environment setup for testing text_editor.py

# Activate virtual environment
source "$(dirname "$0")/venv/bin/activate"

# Set Qt to use offscreen platform (required for headless GUI testing)
export QT_QPA_PLATFORM=offscreen

echo "Environment ready. Run tests with:"
echo "   pytest test_text_editor.py -v"
