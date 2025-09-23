# Echo MCP Server

This is a minimal FastMCP server exposing a single tool:

- `echo()`: Returns a static message every time it is called.

## Requirements
- Python 3.10+
- Install [uv](https://docs.astral.sh/uv/getting-started/installation/) to build and run FastMCP servers.
- Install the MCP inspector tool to access and test your MCP server.
  ```bash
  npx @modelcontextprotocol/inspector
  ```
- kmcp CLI

## Setup

(Recommended) Use a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Init project with kmcp:

```bash
kmcp init python echo-mcp-server
cd echo-mcp-server
```

```bash
kmcp add-tool echo 
```

To simplify, you can copy the `echo.py` file from this repo into `echo-mcp-server/src/tools/echo.py`, replacing the generated one.

```bash
cp ../echo.py src/tools/echo.py
```

## Run the server

To run the server in HTTP mode on `http://localhost:8080/mcp`:

```bash
uv run python src/main.py --transport http --host 0.0.0.0 --port 8080
```

The server will start and listen for MCP http connections.

To run inspector:

```bash
kmcp run
```

Now configure the access to the server:

Transport Type: Streamable HTTP
URL: `http://localhost:8080/mcp`

And test the tool. In this case: `echo`

## Deployment

You can deploy this server to any kubernetes flavored cloud provider.

```bash
kmcp build --platform linux/amd64 --push --tag [my-repo-name]/echo-mcp-server:latest
```

```bash
kmcp deploy echo-mcp-server --image [my-repo-name]/echo-mcp-server:latest --env MESSAGE="This is the mcp server message" -n kagent  --dry-run > echo-mcp-server-deployment.yaml

kubectl apply -f echo-mcp-server-deployment.yaml -n kagent
```