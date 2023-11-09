.PHONY: all
all: fix

.PHONY: check
check:
	# mypy -p plugin
	flake8 .
	black --check --diff --preview .
	isort --check --diff .

.PHONY: fix
fix:
	autoflake --in-place .
	black --preview .
	isort .
