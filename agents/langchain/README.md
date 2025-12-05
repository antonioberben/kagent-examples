**Run (minimal)**

- **Entry point**: `main.py` (FastAPI app)

- **Required env vars**:
  - `LLM_API_KEY` OR `MCP_SERVER` (one required). Without either, requests will fail.
  - Optional: `LLM_API_BASE`, `LLM_MODEL`, `SYSTEM_INSTRUCTION`.

- **Install & run (zsh)**:
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export LLM_API_KEY="sk-..."
export MCP_SERVER=http://localhost:8080/mcp 
export SYSTEM_INSTRUCTION='You are a helpful assistant. Help as much as you can. start your answers with Good Morning.' 
LLM_API_KEY=[YOU_API_KEY] python main.py```


- **Docker (build & run, minimal)**:
```
export MY_REPO_NAME=[my-docker-repo] # replace with your Docker Hub repo name
docker buildx build --platform linux/amd64,linux/arm64  -t ${MY_REPO_NAME}/langchain-agent:latest --push .
```

```bash
docker run --rm -p 10000:10000 \
  -e MCP_SERVER=http://localhost:8080/mcp \
  -e SYSTEM_INSTRUCTION='You are a helpful assistant. Help as much as you can. start your answers with Good Morning.' \
  -e LLM_API_KEY[YOU_API_KEY] \
  ${MY_REPO_NAME}/langchain-agent:latest
```

That's all required to run the agent locally or in Docker.
