# Two stages. The first installs the pinned toolchain and runs the full test
# suite, so an image can only be built from a tree whose tests pass. The second
# carries only the runtime and the package, and runs as an unprivileged user.

# Any Debian or Ubuntu based image with Python 3.10 or newer and pip works.
# The default is the official slim image; override it to build against an
# internal mirror, for example --build-arg BASE_IMAGE=registry.example.org/python:3.12-slim
ARG BASE_IMAGE=python:3.12-slim-bookworm

# ---------------------------------------------------------------- test stage
FROM ${BASE_IMAGE} AS test

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    SOURCE_DATE_EPOCH=0 \
    LC_ALL=C.UTF-8 \
    TZ=UTC

WORKDIR /src
COPY requirements.lock pyproject.toml README.md LICENSE ./
RUN pip install -r requirements.lock
COPY src ./src
COPY tests ./tests
RUN pip install --no-deps . \
 && ruff check src tests \
 && ruff format --check src tests \
 && pytest -q --cov --cov-report=term \
 && signal-harness demo -o /tmp/demo.html

# ------------------------------------------------------------- build wheel
FROM test AS wheel
RUN pip wheel --no-deps --wheel-dir /dist /src

# ------------------------------------------------------------- runtime stage
FROM ${BASE_IMAGE} AS runtime

LABEL org.opencontainers.image.title="signal-harness" \
      org.opencontainers.image.description="Reproducible daily intelligence harness for AI in medicine and biology" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.source="https://github.com/a7med7emedan/signal-harness"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    LC_ALL=C.UTF-8 \
    TZ=UTC

RUN groupadd --system --gid 10001 signal \
 && useradd --system --uid 10001 --gid signal --home-dir /work --create-home signal

COPY --from=wheel /dist /tmp/dist
COPY requirements.lock /tmp/requirements.lock
RUN grep -E '^(Jinja2|MarkupSafe)==' /tmp/requirements.lock > /tmp/runtime.txt \
 && pip install -r /tmp/runtime.txt /tmp/dist/*.whl \
 && rm -rf /tmp/dist /tmp/requirements.lock /tmp/runtime.txt

USER signal
WORKDIR /work

ENTRYPOINT ["signal-harness"]
CMD ["--help"]
