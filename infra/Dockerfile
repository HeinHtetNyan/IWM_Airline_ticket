FROM python:3.11-slim

# Working directory inside container
WORKDIR /app

# Install dependencies first (faster rebuilds)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the whole app code
COPY . .

# Run the app
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${BACKEND_PORT:-8000} --loop uvloop"]
