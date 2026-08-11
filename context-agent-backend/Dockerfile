FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies (curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file and install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app /app/app
COPY alembic /app/alembic
COPY alembic.ini /app/
COPY .env* /app/

# Set Python path to ensure local module imports work correctly
ENV PYTHONPATH=/app

# Expose API port
EXPOSE 8000

# Default command runs the FastAPI server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
