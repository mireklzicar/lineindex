import pytest

def pytest_configure(config):
    config.addinivalue_line(
        "markers", "optional: marks tests that are optional and may be skipped"
    )