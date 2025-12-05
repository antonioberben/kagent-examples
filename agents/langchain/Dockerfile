# Use an official Python base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy agent code
COPY . /app

# Install dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Expose the server port
EXPOSE 10000

# Set environment variables if needed (override with Docker/K8s secrets)
# ENV MCP_SERVER_URL=http://localhost:8080/mcp

# Run the agent server
CMD ["python", "main.py"]