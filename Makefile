MAKEFLAGS += --silent

.PHONY: all
all:

.PHONY: ci-check
ci-check:
 	# mypy -p plugin
	echo "Linting: ruff..."
	ruff check --diff --preview .
	echo "Linting: black..."
	black --diff --preview --check .

.PHONY: ci-fix
ci-fix:
	echo "Fixing: ruff..."
	ruff check --preview --fix .
	# ruff format --preview .
	echo "Fixing: black..."
	black --preview .


.PHONY: update-schema
update-schema:
	python3 ./scripts/update_schema.py
