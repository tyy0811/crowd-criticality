.PHONY: install test gate0a grid
install:
	python -m pip install -e ".[dev]"
test:
	pytest -m "not slow" -q
gate0a:
	python -m critaudit.validation.gate0a
grid:
	python -m critaudit.experiments.recovery_grid
