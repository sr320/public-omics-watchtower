.PHONY: install lint test validate clean

install:
	pip install -e ".[dev]"

lint:
	ruff check watchtower tests

test:
	pytest tests/ -v

validate:
	watchtower config validate

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache .mypy_cache
