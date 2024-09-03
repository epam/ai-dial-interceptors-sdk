PORT ?= 5001
IMAGE_NAME ?= ai-dial-interceptors-sdk
PLATFORM ?= linux/amd64
ARGS=

.PHONY: all install build clean lint format test examples_serve examples_docker_serve

all: build

install:
	poetry install --all-extras
	poetry run codegen

build: install
	poetry build

clean:
	poetry run clean
	poetry env remove --all

publish: build
	poetry publish -u __token__ -p ${PYPI_TOKEN} --skip-existing

lint: install
	poetry run nox -s lint

format: install
	poetry run nox -s format

test: install
	poetry run nox -s test -- $(ARGS)

examples_serve: install
	poetry run uvicorn "examples.app:app" --reload --host "0.0.0.0" --port $(PORT) --workers=1 --env-file ./.env

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
