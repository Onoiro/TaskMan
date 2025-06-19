FROM python:3.8-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY pyproject.toml poetry.lock ./

RUN pip install --upgrade pip && \
    pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --no-dev

COPY . .

FROM python:3.8-slim

RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir /app && useradd -m -r appuser && chown -R appuser /app
WORKDIR /app

COPY --from=builder /usr/local/lib/python3.8/site-packages /usr/local/lib/python3.8/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY --from=builder --chown=appuser:appuser /app /app

USER appuser

EXPOSE 8001

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8001", "task_manager.wsgi:application"]
