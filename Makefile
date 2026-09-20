.PHONY: setup metadata check

setup:
	uv sync --locked --project gitskills-analysis

metadata:
	uv run --python 3.12 --locked --script .plicara/check.py

check: metadata
	uv lock --check --project gitskills-analysis
