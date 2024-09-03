# Stage 1: Builder
FROM python:3.11-slim-buster as builder

# Update and install necessary build dependencies
RUN apt-get update && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    && pip install --upgrade pip \
    && pip install poetry \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies using Poetry
COPY pyproject.toml poetry.lock poetry.toml ./
RUN poetry install --no-interaction --no-ansi --no-cache --no-root --with=main,examples

# Copy the rest of the application
COPY . .
RUN poetry install --no-interaction --no-ansi --no-cache --with=main,examples
RUN poetry run codegen

# Stage 2: Final image
FROM python:3.11-slim-buster as server

# Update and upgrade system packages, including specific security fixes
RUN apt-get update && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    && pip install --upgrade pip \
    && pip install poetry \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the application code and installed dependencies from the builder stage
RUN useradd -m -u 1001 appuser
COPY --chown=appuser --from=builder /app .

# Add and make the entrypoint script executable
COPY ./scripts/docker_entrypoint.sh /docker_entrypoint.sh
RUN chmod +x /docker_entrypoint.sh

# Expose port 5000 and set user
EXPOSE 5000

USER appuser
ENTRYPOINT ["/docker_entrypoint.sh"]

CMD uvicorn examples.app:app --host 0.0.0.0 --port 5000