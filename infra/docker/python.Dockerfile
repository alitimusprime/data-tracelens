FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && addgroup --system app \
    && adduser --system --ingroup app app

COPY services ./services
COPY apps/tracelens_api ./apps/tracelens_api
ENV PYTHONPATH=/app:/app/apps/tracelens_api
USER app

CMD ["python", "-m", "uvicorn", "tracelens.main:app", "--host", "0.0.0.0", "--port", "8080"]
