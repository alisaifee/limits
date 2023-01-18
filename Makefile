lint:
	black --check limits tests
	ruff limits tests
	mypy limits

lint-fix:
	black tests limits
	isort -r --profile=black tests limits
	ruff --fix limits tests 
	mypy limits
