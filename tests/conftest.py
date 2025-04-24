"""Configuration file for pytest that defines custom markers and other test settings."""

def pytest_configure(config):
    """Register custom markers for pytest.
    
    Args:
        config: The pytest configuration object
    """
    config.addinivalue_line(
        "markers", "optional: marks tests that are optional and may be skipped"
    )
