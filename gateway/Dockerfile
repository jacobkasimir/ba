FROM python:3.12-slim

WORKDIR /app

# Install dependencies before copying source code.
# Docker can reuse this layer when only application code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Avoid running the application as root.
RUN useradd --create-home appuser \
    && mkdir -p /app/audit \
    && chown appuser:appuser /app/audit

USER appuser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]