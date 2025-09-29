lint:
	uv run ruff check --select I limits tests doc
	uv run ruff check limits tests doc
	uv run ruff format --check limits tests doc
	uv run mypy limits

lint-fix:
	uv run ruff check --select I --fix limits tests doc
	uv run ruff check --fix limits tests doc
	uv run ruff format limits tests doc
	uv run mypy limits
