# AgentCore Runtime requires linux/arm64 containers listening on 0.0.0.0:8080.
FROM --platform=linux/arm64 python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY agent.py main.py ./

ENV PYTHONUNBUFFERED=1
EXPOSE 8080

# BedrockAgentCoreApp.run() serves POST /invocations + GET /ping on 0.0.0.0:8080.
CMD ["python", "main.py"]
