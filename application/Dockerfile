FROM python:3.12-slim AS base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
# Package the frontend together with the FastAPI application.
COPY static ./static

RUN useradd --create-home appuser \
    && mkdir -p /app/logs \
    && chown appuser:appuser /app/logs

USER appuser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]


FROM base AS test

USER root

COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY tests ./tests

USER appuser

CMD ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider"]


FROM base AS runtime