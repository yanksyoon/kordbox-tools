"""Shared fixtures for GUI tests."""

import os
import pytest


@pytest.fixture(scope="session")
def app():
    """Create QApplication for testing."""
    # Skip GUI tests in CI environments
    if os.getenv("CI") == "true":
        pytest.skip("GUI tests skipped in CI environment")
    
    try:
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app
    except ImportError:
        pytest.skip("PySide6 not available")
    except Exception as e:
        pytest.skip(f"Qt initialization failed: {e}")