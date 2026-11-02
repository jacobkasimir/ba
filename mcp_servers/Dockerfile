# Shared runtime dependencies.
FROM python:3.12-slim AS base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY common ./common
COPY smoke_test.py .

# Metadata services do not require root privileges.
RUN useradd --create-home appuser
USER appuser

# Each runtime target supplies its own "service" package.
CMD ["python", "-m", "service.server"]


# Image containing only the schema service and shared utilities.
FROM base AS schema
COPY schema ./service


# Image containing only the constraints service and shared utilities.
FROM base AS constraints
COPY constraints ./service


# Image containing only the examples service and shared utilities.
FROM base AS examples
COPY examples ./service


# Test image contains all three implementations.
FROM base AS test

USER root

COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY schema ./schema_server
COPY constraints ./constraints_server
COPY examples ./examples_server

COPY tests ./tests

USER appuser

CMD ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider"]