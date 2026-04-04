FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Working directory inside container
WORKDIR /app

# Copy requirements and install
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install pytest for testing (optional, but useful)
RUN pip install pytest pytest-cov pytest-mock

# Copy the whole application code
# It will land in /app/backend (because we copy the 'backend' folder into /app)
COPY backend ./backend

# Create non‑root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

EXPOSE 8000

# The command is overridden by docker‑compose, but we keep a default for safety
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]