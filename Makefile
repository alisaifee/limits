lint:
	ruff check --select I limits tests doc
	ruff check limits tests doc
	ruff format --check limits tests doc
	mypy limits

lint-fix:
	ruff check --select I --fix limits tests doc
	ruff check --fix limits tests doc
	ruff format limits tests doc
	mypy limits
