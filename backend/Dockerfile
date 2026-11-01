# Multi-stage lightweight Python backend image
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code, data fixtures, and alembic migrations
COPY app/ ./app/
COPY data/ ./data/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Environment defaults
ENV HOST=0.0.0.0
ENV PORT=8000
ENV PYTHONPATH=/app

EXPOSE 8000

# Run FastAPI production ASGI server with uvicorn honoring $PORT
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
