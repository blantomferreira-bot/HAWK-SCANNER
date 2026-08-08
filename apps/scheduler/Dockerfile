FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/apps/scheduler

WORKDIR /app
COPY apps/scheduler/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY apps/scheduler /app/apps/scheduler

CMD ["python", "-m", "hawk_scheduler.main"]
