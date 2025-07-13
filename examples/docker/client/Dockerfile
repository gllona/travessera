FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# First, install travessera from the repository context
COPY . /tmp/travessera-repo
RUN cd /tmp/travessera-repo && pip install -e .

# Copy client application
COPY examples/docker/client/client.py .

# Create a non-root user for security
RUN useradd -m -u 1000 clientuser && chown -R clientuser:clientuser /app
USER clientuser

# Default command (can be overridden in docker-compose)
CMD ["python", "client.py"]