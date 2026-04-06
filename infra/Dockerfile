FROM python:3.11-slim-bullseye 
#added bullseye becoz of connection issues with debian repositories

# Install system dependencies
RUN sed -i 's|http://deb.debian.org|http://cloudfront.debian.net|g' /etc/apt/sources.list && \
    apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*
#added "sed -i 's|http://deb.debian.org|http://cloudfront.debian.net|g' /etc/apt/sources.list && \" to fix connection issues with debian repositories"

# Working directory inside container
WORKDIR /app

# Copy requirements and install
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

#Deleted Run pip install pytest pytest-cov pytest-mock (becoz pytest is already in requirements.txt)

# Copy the whole application code
# It will land in /app/backend (because we copy the 'backend' folder into /app)
COPY backend ./backend

# Create non‑root user for security
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/uploads && \
    chown -R appuser:appuser /app
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
