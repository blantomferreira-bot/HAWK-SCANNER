FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/apps/api:/app/apps/worker

WORKDIR /app
COPY apps/api/requirements.txt /app/apps/api/requirements.txt
COPY apps/worker/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY apps/api /app/apps/api
COPY apps/worker /app/apps/worker

EXPOSE 8001
CMD ["uvicorn", "hawk_worker.main:app", "--host", "0.0.0.0", "--port", "8001", "--proxy-headers"]
