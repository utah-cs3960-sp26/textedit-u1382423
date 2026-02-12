#!/bin/bash
# Environment setup for testing text_editor.py

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Activate virtual environment
source "$SCRIPT_DIR/venv/bin/activate"

# Install required dependencies
pip install pytest pytest-qt pytest-timeout pytest-cov pytest-subtests PyQt5 --quiet

# Set Qt platform - use xcb if DISPLAY is set, otherwise offscreen
if [ -n "$DISPLAY" ]; then
    export QT_QPA_PLATFORM=xcb
else
    export QT_QPA_PLATFORM=offscreen
fi

echo "Environment ready. Run tests with:"
echo "   pytest testing/test_text_editor.py -v"
