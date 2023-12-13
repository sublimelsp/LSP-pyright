.PHONY: all
all: fix

.PHONY: ci-check
ci-check:
	# mypy -p plugin
	flake8 .
	black --check --diff --preview .
	isort --check --diff .

.PHONY: ci-fix
ci-fix:
	autoflake --in-place .
	black --preview .
	isort .

.PHONY: update-schema
update-schema:
	python3 ./scripts/update_schema.py
