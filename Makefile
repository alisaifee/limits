lint:
	black --check limits tests
	flake8 limits tests
	mypy limits

lint-fix:
	black tests limits
	isort -r --profile=black tests limits
	autoflake8 -i -r tests limits
	mypy limits
