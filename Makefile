lint:
	ruff check --select I limits tests
	ruff check limits tests
	ruff format --check limits tests
	mypy limits

lint-fix:
	ruff check --select I --fix limits tests
	ruff check --fix limits tests
	ruff format limits tests
	mypy limits
