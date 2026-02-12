"""Pytest configuration for text editor tests."""

import pytest
import os

# Use offscreen platform for headless testing
os.environ['QT_QPA_PLATFORM'] = 'offscreen'


def pytest_collection_modifyitems(items):
    """Add 30 second timeout to all tests."""
    for item in items:
        if not any(marker.name == 'timeout' for marker in item.iter_markers()):
            item.add_marker(pytest.mark.timeout(30))
