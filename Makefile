.PHONY: all
all: fix

.PHONY: check
check:
	# mypy -p plugin
	flake8 .
	black --check --diff .
	isort --check --diff .

.PHONY: fix
fix:
	autoflake --in-place .
	black .
	isort .
