install:
	poetry install --all-extras

lint: install
	poetry run nox -s lint

format: install
	poetry run nox -s format

test: install
	poetry run nox -s test

help:
	@echo '===================='
	@echo '-- LINTING --'
	@echo 'format                       - run code formatters'
	@echo 'lint                         - run linters'
	@echo '-- TESTING --'
	@echo 'test                         - run tests'
