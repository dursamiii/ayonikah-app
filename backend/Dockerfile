FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY backend/requirements.txt /opt/backend/requirements.txt
RUN pip install --no-cache-dir -r /opt/backend/requirements.txt
COPY backend /app/backend

ENV DATABASE_PATH=/data/planner.sqlite3 \
    UPLOAD_DIR=/data/uploads
RUN mkdir -p /data/uploads && useradd --system --uid 10001 appuser \
    && chown -R appuser:appuser /data
USER appuser

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)" || exit 1

# DB and uploads share one writable persistent data volume.
