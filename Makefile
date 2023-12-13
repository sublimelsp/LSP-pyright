.PHONY: all
all:

.PHONY: ci-check
ci-check:
 	# mypy -p plugin
	ruff check --diff --preview .
	black --diff --preview --check .

.PHONY: ci-fix
ci-fix:
	ruff check --preview --fix .
	# ruff format --preview .
	black --preview .


.PHONY: update-schema
update-schema:
	python3 ./scripts/update_schema.py
