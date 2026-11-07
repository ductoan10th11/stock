FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1 HOME=/tmp
WORKDIR /app

COPY requirements.txt .
# The API server and its test tools are not needed for notebooks.
RUN grep -vE '^(fastapi|uvicorn|httpx|pytest)==' requirements.txt > requirements-notebook.txt \
    && pip install -r requirements-notebook.txt

EXPOSE 8888
