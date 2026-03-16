PORT ?= 5001
IMAGE_NAME ?= ai-dial-interceptors-sdk
PLATFORM ?= linux/amd64
VENV_DIR ?= .venv
POETRY ?= poetry
POETRY_PYTHON ?= python
ARGS=

.PHONY: all init_env install build clean lint format test integration_tests examples_serve examples_docker_serve

-include .env.dev
export

all: build

init_env:
	$(POETRY) env use $(POETRY_PYTHON)

install: init_env
	$(POETRY) install --all-extras
	$(POETRY) run codegen

build: install
	$(POETRY) build

clean:
	$(POETRY) run clean
	$(POETRY) env remove --all

publish: build
	$(POETRY) publish -u __token__ -p $(PYPI_TOKEN) --skip-existing

lint: install
	$(POETRY) run nox -s lint

format: install
	$(POETRY) run nox -s format

test: install
	$(POETRY) run nox -s test $(if $(PYTHON),--python=$(PYTHON),)

integration_tests: install
	$(POETRY) run nox -s integration_tests

examples_serve: install
	$(POETRY) run uvicorn "aidial_interceptors_sdk.examples.app:app" --reload --host "0.0.0.0" --port $(PORT) --workers=1 --env-file ./.env

examples_docker_serve:
	docker build --platform $(PLATFORM) -t $(IMAGE_NAME):dev .
	docker run --platform $(PLATFORM) --env-file ./.env --rm -p $(PORT):5000 $(IMAGE_NAME):dev

help:
	@echo '===================='
	@echo 'build                        - build the source and wheels archives'
	@echo 'clean                        - clean virtual env and build artifacts'
	@echo 'publish                      - publish the library to PyPi'
	@echo '-- LINTING --'
	@echo 'format                       - run code formatters'
	@echo 'lint                         - run linters'
	@echo '-- RUNNING EXAMPLES --'
	@echo 'examples_serve               - run the dev server with examples locally'
	@echo 'examples_docker_serve        - run the dev server with examples from the docker'
	@echo '-- TESTS --'
	@echo 'test                         - run unit tests'
