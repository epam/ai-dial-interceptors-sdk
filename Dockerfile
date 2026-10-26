# Stage 1: Builder
FROM python:3.11-alpine AS builder

RUN apk update && apk upgrade --no-cache libcrypto3 libssl3
RUN pip install poetry==2.1.1

# Only install pre-built wheels. All dependencies ship musllinux wheels,
# so no compilation is needed and no build toolchain (alpine-sdk) is required.
# Fails fast if a package ever lacks a wheel instead of silently compiling.
RUN poetry config installer.only-binary :all:

WORKDIR /app

# Install dependencies using Poetry
COPY pyproject.toml poetry.lock poetry.toml ./
# --only=main: the runtime image needs the main group and the examples extra only.
# --with=main would ADD main to the default set, dragging the dev/test/lint groups
# (nox, pre-commit, pytest, pyright, ruff and their virtualenv dep) into the image.
RUN poetry install --no-interaction --no-ansi --no-cache --no-root --only=main --extras=examples

# Copy the rest of the application
COPY . .
RUN poetry install --no-interaction --no-ansi --no-cache --only=main --extras=examples
RUN poetry run codegen

# pip is not needed at runtime; removing it fixes all pip CVEs.
RUN .venv/bin/python -m pip uninstall -y pip

# Stage 2: Final image
FROM python:3.11-alpine AS server

RUN apk update && apk upgrade --no-cache libcrypto3 libssl3
# fix CVE-2023-52425
RUN apk upgrade --no-cache libexpat
# fix CVE-2026-23949 and CVE-2026-59890 and GHSA-xmj3-9gf7-h52w
RUN pip install setuptools==84.2.1
# fix CVE-2026-24049
RUN pip install wheel==0.46.2
# fix CVE-2025-6965 and CVE-2026-22184 and CVE-2026-40200
RUN apk upgrade --no-cache sqlite-libs zlib musl musl-utils

# pip is not needed at runtime; removing it fixes all pip CVEs.
# Must stay after the last pip usage.
RUN pip uninstall -y pip

WORKDIR /app

# Copy the application code and installed dependencies from the builder stage
RUN adduser -u 1001 --disabled-password --gecos "" appuser
COPY --chown=appuser --from=builder /app .

# Add and make the entrypoint script executable
COPY ./scripts/docker_entrypoint.sh /docker_entrypoint.sh
RUN chmod +x /docker_entrypoint.sh

# Expose port 5000 and set user
EXPOSE 5000

USER appuser
ENTRYPOINT ["/docker_entrypoint.sh"]

HEALTHCHECK  --interval=10s --timeout=5s --start-period=30s --retries=6 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:5000/health || exit 1

CMD ["uvicorn", "aidial_interceptors_sdk.examples.app:app", "--host", "0.0.0.0", "--port", "5000"]
