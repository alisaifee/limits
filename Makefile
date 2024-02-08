lint:
	ruff check --select I
	ruff format --check limits tests
	ruff limits tests
	mypy limits

lint-fix:
	ruff check --select I --fix
	ruff format limits tests
	ruff --fix limits tests 
	mypy limits
