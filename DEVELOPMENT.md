# Development Guide

This document provides instructions for developing, testing, and publishing the LineIndex package.

## Setting Up Development Environment

1. Clone the repository:
   ```bash
   git clone https://github.com/mireklzicar/lineindex.git
   cd lineindex
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

## Running Tests

The package uses pytest for testing. You can run the tests in several ways:

### Basic test run:
```bash
pytest
```

### Run with coverage report:
```bash
pytest --cov=lineindex
```

### Run with verbose output:
```bash
pytest -v
```

### Run specific test file:
```bash
pytest tests/test_lineindex.py
```

### Run tests in parallel:
```bash
pytest -xvs -n auto
```

## Linting and Formatting

The code should follow PEP 8 style guidelines. Run these commands to ensure proper formatting:

```bash
# Check code style with flake8
flake8 lineindex tests

# Format code with black
black lineindex tests

# Sort imports with isort
isort lineindex tests
```

## Building Documentation

The documentation is built using Sphinx:

```bash
# Generate API documentation
sphinx-apidoc -o docs/ lineindex

# Build HTML documentation
cd docs
make html
cd ..

# View documentation in browser
open docs/_build/html/index.html  # On Windows: start docs/_build/html/index.html
```

## Pre-Publish Checklist

Before making your first commit or publishing to PyPI, make sure to:

1. **Run all tests**:
   ```bash
   # Run all tests with different Python versions if available
   tox
   
   # Or just with the current Python version
   pytest
   ```

2. **Verify installation works**:
   ```bash
   # Install from local directory
   pip install -e .
   
   # Try basic functionality
   lineindex example
   lineindex example.txt 0:10
   ```

3. **Try with compression**:
   ```bash
   # Install compression dependencies
   pip install -e ".[compression]"
   
   # Test compression
   lineindex file example.txt --compress
   lineindex file example.txt.dz 0:10
   ```

4. **Check distribution builds correctly**:
   ```bash
   # Build distribution
   python -m build
   
   # Check contents of distribution
   tar tzf dist/*.tar.gz | sort
   ```

5. **Validate package structure**:
   ```bash
   # Install twine for validation
   pip install twine
   
   # Validate package
   twine check dist/*
   ```

6. **Verify documentation builds**:
   ```bash
   cd docs
   make html
   # Check that there are no warnings
   ```

7. **Test CLI commands**:
   ```bash
   # Test example command
   lineindex example
   
   # Test file command
   lineindex file example.txt 0:10
   
   # Test legacy syntax
   lineindex example.txt 0:10
   ```

8. **Test package in a clean environment**:
   ```bash
   # Create a temporary directory
   mkdir ~/lineindex-test
   cd ~/lineindex-test
   
   # Create a fresh virtual environment
   python -m venv test-venv
   source test-venv/bin/activate  # On Windows: test-venv\Scripts\activate
   
   # Install from the built distribution
   pip install /path/to/your/lineindex/dist/lineindex-0.1.0.tar.gz
   
   # Test functionality
   lineindex example
   lineindex example.txt 0:10
   ```

## Publishing

Once you've completed all checks, you can publish the package:

1. First, test the publishing process on TestPyPI:
   ```bash
   # Upload to TestPyPI
   python -m twine upload --repository-url https://test.pypi.org/legacy/ dist/*
   
   # Install from TestPyPI
   pip install --index-url https://test.pypi.org/simple/ lineindex
   ```

2. If everything looks good, publish to PyPI:
   ```bash
   # Upload to PyPI
   python -m twine upload dist/*
   ```

3. After publishing, verify the installation works from PyPI:
   ```bash
   pip install lineindex
   lineindex example
   lineindex example.txt 0:10
   ```

## CI/CD Workflow

The GitHub Actions workflow will:
1. Run tests on multiple Python versions
2. Bump the version on merge to main
3. Build and publish the package to PyPI

Ensure your PyPI API token is set as a GitHub secret named `PYPI_API_TOKEN`.