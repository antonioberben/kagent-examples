FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt ./


RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Note socks support for requests, in case it is integrated with Istio or similar proxies
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install 'requests[socks]' --no-cache-dir

COPY main.py ./

# For stdio transport, an MCP client should spawn this container and stream stdio.
CMD ["python", "main.py"]