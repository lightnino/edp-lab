.PHONY: setup check verify-raw sql test lint
setup:
	uv sync
check:
	uv run python -m edp_lab check-env
verify-raw:
	uv run python -m edp_lab verify-raw
sql:
	uv run python -m edp_lab sql sql/raw/00_healthcheck.sql
test:
	uv run pytest -q
lint:
	uv run ruff check .
