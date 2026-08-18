.PHONY: install run debug clean lint lint-strict

PYTHON := python3
MAP ?= maps/easy/01_linear_path.txt

install:
	$(PYTHON) -m pip install -e ".[dev]"

run:
	$(PYTHON) -m src $(MAP)

debug:
	$(PYTHON) -m pdb -m src $(MAP)

clean:
	find . -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete
	find . -type d -name "__pycache__" -empty -delete
	rm -rf .mypy_cache .pytest_cache .ruff_cache
	rm -rf src/*.egg-info

lint:
	flake8 .
	mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	flake8 .
	mypy . --strict
