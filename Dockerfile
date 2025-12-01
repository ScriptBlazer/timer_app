FROM --platform=linux/amd64 python:3.11-slim AS builder-base

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings

RUN apt update && \
    apt upgrade -y && \
    apt install -y --no-install-recommends curl && \
    apt clean  && \
    apt autoremove -y && \
    apt purge -y --auto-remove && \
    rm -rf /var/lib/apt/lists/* && \
    addgroup --system app && \
    adduser --system --group app


FROM builder-base AS python-base

# OS deps needed to compile Python dependencies
RUN apt update && \
    apt install --no-install-recommends --yes --quiet \
    build-essential \
    gcc g++ \
    libpq-dev \
    libffi-dev \
    git && \
    rm -rf /var/lib/apt/lists/*

# Virtualenv
RUN python3 -m venv /venv && \
    pip install --no-cache-dir --upgrade pip setuptools wheel

# Python deps
COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


FROM builder-base AS app-base

WORKDIR /app

# Copy venv from previous stage
COPY --chown=app:app --from=python-base /venv /venv

# Copy project
COPY . .

# Make sure app user owns everything
RUN chown -R app:app /app

# Run as non-root
USER app:app

EXPOSE 8000

ENTRYPOINT [ "/app/docker/entrypoints/web.sh" ]