FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /workspace

COPY documentation/requirements.txt /tmp/documentation-requirements.txt
RUN pip install --no-cache-dir -r /tmp/documentation-requirements.txt

COPY documentation/docs_pipeline.py /usr/local/bin/docs_pipeline.py
COPY documentation/watch_docs.py /usr/local/bin/watch_docs.py

CMD ["python", "/usr/local/bin/watch_docs.py"]
