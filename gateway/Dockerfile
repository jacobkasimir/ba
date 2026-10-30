# Shared application image.
FROM python:3.12-slim AS base

WORKDIR /app

# Avoid writing Python bytecode into application directories.
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Run the application without root privileges.
RUN useradd --create-home appuser \
    && mkdir -p /app/audit \
    && chown appuser:appuser /app/audit

USER appuser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]


# Separate test image. These credentials are deliberately fake.
FROM base AS test

USER root

COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY tests ./tests

ENV DB_HOST=unused
ENV DB_PORT=5432
ENV DB_NAME=aktin
ENV DB_USER=user
ENV MIN_CELL_COUNT=5
ENV AUDIT_PATH=/tmp/test-audit.sqlite

USER appuser

CMD ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider"]


# Keep runtime last so ordinary Compose builds start the API, not tests.
FROM base AS runtime