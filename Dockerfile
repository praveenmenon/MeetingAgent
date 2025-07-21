# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY meeting_agent.py .
COPY config/ ./config/

# Create non-root user for security
RUN useradd -m -u 1000 meetingagent && \
    chown -R meetingagent:meetingagent /app
USER meetingagent

# Expose port (if needed for future web interface)
EXPOSE 8000

# Default command
CMD ["python", "meeting_agent.py"]