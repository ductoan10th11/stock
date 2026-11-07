FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY requirements.txt .
# Jupyter packages are only needed for notebooks, not for the API.
RUN grep -vE '^(ipykernel|nbconvert|notebook)==' requirements.txt > requirements-api.txt \
    && pip install -r requirements-api.txt

COPY scripts scripts
COPY apps/api apps/api

WORKDIR /app/apps/api
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
