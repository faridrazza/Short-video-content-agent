# Multi-Agent Video Generation System Dockerfile
# Based on Python 3.12 slim for optimal performance and security

FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=8080
ENV PYTHONPATH=/app
# Set the service account credentials path
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/service-account-key.json.json

# Install system dependencies required for video processing
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app

# Set work directory
WORKDIR /app

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs sessions output && \
    chown -R app:app /app

# Switch to non-root user
USER app

# Expose port
EXPOSE $PORT

# Start the application using ADK web interface pointing to current directory
# This allows ADK to find the agents folder and all dependencies
CMD ["adk", "web", "--host", "0.0.0.0", "--port", "8080", "."] 