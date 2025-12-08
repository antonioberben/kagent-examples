# Use an official Python base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Copy agent code
COPY . /app

# Install dependencies from requirements.txt
# Note socks support for requests, in case it is integrated with Istio or similar proxies
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install 'requests[socks]' --no-cache-dir

# Expose the server port
EXPOSE 10000

# Set environment variables if needed (override with Docker/K8s secrets)
# ENV MCP_SERVER_URL=http://localhost:8080/mcp

# Run the agent server
CMD ["python", "main.py"]