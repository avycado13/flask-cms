FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

ENV FLASK_APP=flaskcms.py
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Create virtual environment
RUN python -m venv /app/.venv

# Use venv binaries
ENV PATH="/app/.venv/bin:$PATH"

# Copy dependency files before installing
COPY pyproject.toml uv.lock ./

# Install dependencies into venv
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

COPY . /app

SHELL ["/bin/bash", "-c"]

# Compile Flask-Babel translations
RUN flask translate compile

ENTRYPOINT ["./run.sh"]
