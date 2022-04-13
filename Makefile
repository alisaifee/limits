lint:
	black --check limits tests
	mypy limits
	flake8 limits tests

lint-fix:
	black tests limits
	mypy limits
	isort -r --profile=black tests limits
	autoflake8 -i -r tests limits
