FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY pyproject.toml poetry.lock README.md ./

RUN pip install --upgrade pip && \
    pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-root --no-interaction --no-ansi --without dev

COPY . .

RUN poetry install --no-interaction --no-ansi --without dev

FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir /app && useradd -m -r appuser && chown -R appuser /app
WORKDIR /app

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY --from=builder --chown=appuser:appuser /app /app

USER appuser

EXPOSE 8001

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8001", "--access-logfile", "-", "--error-logfile", "-", "task_manager.wsgi:application"]
