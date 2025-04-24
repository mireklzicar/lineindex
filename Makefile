.PHONY: clean clean-build clean-pyc clean-test lint test test-all coverage docs dist install

help:
	@echo "clean - remove all build, test, coverage and Python artifacts"
	@echo "clean-build - remove build artifacts"
	@echo "clean-pyc - remove Python file artifacts"
	@echo "clean-test - remove test and coverage artifacts"
	@echo "lint - check style with flake8, black, and isort"
	@echo "test - run tests quickly with the default Python"
	@echo "test-all - run tests on every Python version with tox"
	@echo "coverage - check code coverage quickly with the default Python"
	@echo "docs - generate Sphinx HTML documentation"
	@echo "dist - package"
	@echo "install - install the package to the active Python's site-packages"

clean: clean-build clean-pyc clean-test

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test:
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/
	rm -fr .pytest_cache

lint:
	flake8 lineindex tests
	black --check lineindex tests
	isort --check lineindex tests

format:
	black lineindex tests
	isort lineindex tests

test:
	pytest

test-all:
	tox

coverage:
	pytest --cov=lineindex --cov-report=html
	@echo "Open htmlcov/index.html to view report"

docs:
	rm -f docs/lineindex.rst
	rm -f docs/modules.rst
	sphinx-apidoc -o docs/ lineindex
	$(MAKE) -C docs clean
	$(MAKE) -C docs html
	@echo "Open docs/_build/html/index.html to view documentation"

dist: clean
	python -m build
	ls -l dist

install: clean
	pip install .

dev-install:
	pip install -e ".[dev]"