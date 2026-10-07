# Targets assume a POSIX shell. On Windows use the Docker image or WSL.

PYTHON ?= python3
VENV   ?= .venv
BIN    := $(VENV)/bin
IMAGE  ?= signal-harness
TAG    ?= 1.0.0
BASE_IMAGE ?= python:3.12-slim-bookworm
EXPECTED := $(shell cut -d' ' -f1 src/signal_harness/examples/issue.sample.sha256)

.PHONY: help setup lint format test demo verify check docker docker-run clean

help:
	@echo "setup       create $(VENV) with pinned dependencies"
	@echo "lint        ruff check and format check"
	@echo "format      apply ruff formatting"
	@echo "test        pytest with the coverage floor"
	@echo "demo        render and gate the bundled example"
	@echo "verify      compare the demo output with the published checksum"
	@echo "check       lint, test and verify"
	@echo "docker      build the image (runs the checks inside it)"
	@echo "docker-run  render the demo with the image into ./build"
	@echo "clean       remove build output and caches"

$(BIN)/signal-harness: requirements.lock pyproject.toml
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install -r requirements.lock
	$(BIN)/pip install --no-deps -e .
	@touch $@

setup: $(BIN)/signal-harness

lint: setup
	$(BIN)/ruff check
	$(BIN)/ruff format --check

format: setup
	$(BIN)/ruff format

test: setup
	$(BIN)/pytest -q --cov

demo: setup
	$(BIN)/signal-harness demo -o build/demo.html

verify: demo
	@actual=$$($(PYTHON) -c "import hashlib,sys;print(hashlib.sha256(open('build/demo.html','rb').read()).hexdigest())"); \
	if [ "$$actual" = "$(EXPECTED)" ]; then echo "reproducible: $$actual"; \
	else echo "checksum mismatch: got $$actual, expected $(EXPECTED)"; exit 1; fi

check: lint test verify

docker:
	docker build --build-arg BASE_IMAGE=$(BASE_IMAGE) -t $(IMAGE):$(TAG) -t $(IMAGE):latest .

docker-run:
	mkdir -p build
	docker run --rm --user "$$(id -u):$$(id -g)" -v "$$PWD/build:/work" $(IMAGE):$(TAG) demo -o /work/demo.html

clean:
	rm -rf build dist .coverage htmlcov .pytest_cache .ruff_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
