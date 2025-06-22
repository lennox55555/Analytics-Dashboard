FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file and install Python dependencies
COPY config/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p static templates certs logs

# Set PYTHONPATH to include src directory
ENV PYTHONPATH="${PYTHONPATH}:/app/src:/app"

# Expose ports
EXPOSE 80 443

# Start the application
CMD ["python", "-m", "src.app"]