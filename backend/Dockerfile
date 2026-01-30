FROM python:3.11-bookworm

# create working directory
WORKDIR /app

# install dependencies
COPY requirements.txt .
RUN python -m pip install --no-cache-dir "pip==24.3.1" setuptools wheel
RUN python -m pip install --no-cache-dir -r requirements.txt

# copy application
COPY app ./app

# expose port
EXPOSE 8000

# run fastapi
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
