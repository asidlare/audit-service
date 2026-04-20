FROM python:3.13 AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
# build dependencies for cassandra-driver
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libev-dev \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /code
COPY pyproject.toml .
RUN uv sync --no-dev --no-install-project

FROM python:3.13-slim
# Runtime dependencies dla cassandra-driver
RUN apt-get update && apt-get install -y --no-install-recommends \
    libev4 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /code
COPY --from=builder /code/.venv /usr/local/.venv
COPY . .
ENV PATH="/usr/local/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
