# TPMS Sensor Data Simulator - Docker Container
# Build: docker build -t tpms-simulator .
# Run: docker run -v $(pwd)/output:/app/output tpms-simulator [arguments]

# Use Python 3.9 slim image as base
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies for geospatial packages
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    gdal-bin \
    libgdal-dev \
    libspatialindex-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements files
COPY requirements.txt requirements-minimal.txt ./

# Install Python dependencies
# Try full installation first, fallback to minimal if it fails
RUN pip install --no-cache-dir -r requirements.txt || \
    pip install --no-cache-dir -r requirements-minimal.txt

# Copy application files
COPY tpms_simulator.py example_usage.py ./

# Create output directory
RUN mkdir -p /app/output

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV OUTPUT_DIR=/app/output

# Default command (show help)
ENTRYPOINT ["python", "tpms_simulator.py"]
CMD ["--help"]