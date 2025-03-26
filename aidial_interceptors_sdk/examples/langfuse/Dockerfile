FROM python:3.13.2

RUN apt-get update && apt-get upgrade -y \
&& pip install --upgrade pip \
&& pip install poetry==2.0.1 \
&& apt-get install openssl -y

WORKDIR /app

# Install dependencies using Poetry
COPY pyproject.toml poetry.lock poetry.toml ./
RUN poetry install --no-interaction --no-ansi --no-root

COPY ai_dial_interceptors_langfuse/ /app/ai_dial_interceptors_langfuse

EXPOSE 8080
CMD ["poetry", "run", "uvicorn", "ai_dial_interceptors_langfuse.app:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]
