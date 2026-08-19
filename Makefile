# Interpreter used by every target. Override per-environment, e.g.:
#   make test PYTHON=python3.11
# Bare `python` is deliberately avoided: it does not exist on a stock macOS PATH
# (/usr/bin/python was removed in 12.3) and elsewhere resolves to whatever is first
# on PATH, so it can silently select a different interpreter than the one the package
# was installed into. `pytest` is invoked as `$(PYTHON) -m pytest` for the same reason.
PYTHON ?= python3

.PHONY: install test gate0a grid
install:
	$(PYTHON) -m pip install -e ".[dev]"
test:
	$(PYTHON) -m pytest -m "not slow" -q
gate0a:
	$(PYTHON) -m critaudit.validation.gate0a
grid:
	$(PYTHON) -m critaudit.experiments.recovery_grid
