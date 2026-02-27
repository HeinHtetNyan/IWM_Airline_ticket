FROM python:3.11-slim

# Working directory inside container
WORKDIR /app

# Install dependencies first (faster rebuilds)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the whole app code
COPY . .

# Expose the port FastAPI listens on
EXPOSE 8000

# Run the app
#CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
#CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000",  "--loop", "uvloop"]
