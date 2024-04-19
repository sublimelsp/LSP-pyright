MAKEFLAGS += --silent

.PHONY: all
all:

.PHONY: ci-check
ci-check:
	# @echo "========== check: mypy =========="
	# mypy -p plugin
	@echo "========== check: ruff (lint) =========="
	ruff check --diff .
	@echo "========== check: ruff (format) =========="
	ruff format --diff .

.PHONY: ci-fix
ci-fix:
	@echo "========== fix: ruff (lint) =========="
	ruff check --fix .
	@echo "========== fix: ruff (format) =========="
	ruff format .

.PHONY: update-schema
update-schema:
	python3 ./scripts/update_schema.py
