VENV := venv
PYTHON := $(VENV)/bin/python3
PIP := $(VENV)/bin/pip
FLAKE8 := $(VENV)/bin/flake8
BLACK := $(VENV)/bin/black
ISORT := $(VENV)/bin/isort

.PHONY: help venv install lint lint-check format install-hooks clean

help:
	@echo "Secret Santa - Available targets:"
	@echo "  make venv          - Create Python virtual environment"
	@echo "  make install       - Install dependencies in venv"
	@echo "  make lint          - Run all linting checks"
	@echo "  make lint-check    - Run linting checks without fixing"
	@echo "  make format        - Format code (black + isort)"
	@echo "  make install-hooks - Install git pre-commit hooks"
	@echo "  make clean         - Remove log files and cache"
	@echo "  make clean-all     - Remove venv, logs, and cache"

venv:
	@if [ ! -d "$(VENV)" ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv $(VENV); \
		echo "✓ Virtual environment created"; \
	else \
		echo "Virtual environment already exists"; \
	fi

install: venv
	@echo "Installing dependencies..."
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install flake8 black isort
	@echo "✓ Dependencies installed"

lint: lint-check format
	@echo "✓ Linting complete"

lint-check: venv
	@echo "Running flake8..."
	$(FLAKE8) secret-santa.py secret-santa-eum.py --max-line-length=88 --extend-ignore=E203,W503
	@echo "Checking code formatting with black..."
	$(BLACK) --check secret-santa.py secret-santa-eum.py
	@echo "Checking import order with isort..."
	$(ISORT) --check-only secret-santa.py secret-santa-eum.py

format: venv
	@echo "Formatting code with black..."
	$(BLACK) secret-santa.py secret-santa-eum.py
	@echo "Sorting imports with isort..."
	$(ISORT) secret-santa.py secret-santa-eum.py

install-hooks:
	@echo "Installing git pre-commit hook..."
	@mkdir -p .git/hooks
	@echo '#!/bin/sh' > .git/hooks/pre-commit
	@echo 'make lint-check' >> .git/hooks/pre-commit
	@chmod +x .git/hooks/pre-commit
	@echo "✓ Pre-commit hook installed"

clean:
	rm -f results.log
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete

clean-all: clean
	rm -rf $(VENV)
	@echo "✓ Removed virtual environment"
