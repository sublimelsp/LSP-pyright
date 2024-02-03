MAKEFLAGS += --silent

.PHONY: all
all:

.PHONY: ci-check
ci-check:
 	# mypy -p plugin
	echo "Check: ruff (lint)"
	ruff check --diff --preview .
	echo "Check: ruff (format)"
	ruff format --diff --preview .

.PHONY: ci-fix
ci-fix:
	echo "Fix: ruff (lint)"
	ruff check --preview --fix .
	echo "Fix: ruff (format)"
	ruff format --preview .

.PHONY: update-schema
update-schema:
	python3 ./scripts/update_schema.py
