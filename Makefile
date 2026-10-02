# SPDX-FileCopyrightText: Copyright (C) 2026 Renegade Penguin LLC
# SPDX-License-Identifier: GPL-3.0-or-later

# Everything CI runs, runnable here.

PY ?= .venv/bin/python
UNIT_DIR ?= $(HOME)/.config/systemd/user

.PHONY: help venv lint format typecheck test check build install-user clean

help:
	@echo "make venv         - .venv with the dev tools"
	@echo "make lint         - ruff check + ruff format --check"
	@echo "make typecheck    - mypy --strict"
	@echo "make test         - pytest (loopback only)"
	@echo "make check        - all three. Run before pushing."
	@echo "make build        - wheel and sdist"
	@echo "make install-user - copy the user unit to $(UNIT_DIR) (does not enable it)"

venv:
	python3 -m venv .venv
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -e ".[dev]"

lint:
	$(PY) -m ruff check src tests
	$(PY) -m ruff format --check src tests

format:
	$(PY) -m ruff format src tests

typecheck:
	$(PY) -m mypy

test:
	$(PY) -m pytest -W error::DeprecationWarning

check: lint typecheck test
	@echo "all checks passed"

build:
	$(PY) -m build

# Copies the unit and prints the next step; it neither enables nor starts it.
# The unit runs %h/.local/bin/hammunition-gps-tether, where `pip install --user`
# or `pipx install` puts the program.
install-user:
	install -d $(UNIT_DIR)
	install -m 0644 systemd/hammunition-gps-tether.service $(UNIT_DIR)/hammunition-gps-tether.service
	@echo "Installed $(UNIT_DIR)/hammunition-gps-tether.service. To start it now and at login:"
	@echo "  systemctl --user daemon-reload && systemctl --user enable --now hammunition-gps-tether.service"

clean:
	rm -rf dist build .pytest_cache .ruff_cache .mypy_cache src/*.egg-info
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
