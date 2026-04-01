
# FastMCP HTTPBin Example Server

This is a minimal [FastMCP] server that exposes a tool for interacting with an external [HttpBin](https://httpbin.org/) service. The server is designed to demonstrate how to wrap external HTTP APIs as MCP tools, making them accessible to MCP-capable clients.

## Available Tools

- **httpbin_get()**: Calls the `/get` endpoint on the configured `HTTPBIN_HOST` and returns the JSON response. This tool is useful for testing HTTP requests and inspecting headers, query parameters, and other request details. The server must be started with the `HTTPBIN_HOST` environment variable set to the base URL of your HttpBin service (e.g., `https://httpbin.org`).

## What does the MCP server do?

The MCP server exposes its tools over HTTP (by default on port 8080). MCP clients can invoke these tools remotely, and the server will execute the corresponding Python function, returning the result. In this example, the server provides a single tool that makes an authenticated HTTP request to an external service and returns the result to the client.

## Run

1. Create and activate a virtualenv:
	```bash
	python3 -m venv .venv
	source .venv/bin/activate
	```

2. Install dependencies:
	```bash
	pip install -U pip
	pip install -r requirements.txt
	```

	This installs the OpenTelemetry launcher binary (`opentelemetry-instrument`) that kagent injects when tracing is enabled.

3. Set the required environment variable:
	```bash
	export HTTPBIN_HOST="https://httpbin.org"
	```

4. Start the MCP server (HTTP transport, port 8080):
	```bash
	python main.py
	```

	To validate the same startup path that kagent uses, run:
	```bash
	opentelemetry-instrument python main.py
	```

The server will expose its MCP tools at `http://localhost:8080/mcp`. You can use any MCP-capable client to invoke the `httpbin_get` tool.

### Run locally (quick)

If you just want a one-liner to run the server locally without creating a virtualenv, use:

```bash
HTTPBIN_HOST="https://httpbin.org" python main.py
```


## Run with Docker

1. Build the image:
	```bash
	export MY_REPO_NAME=[my-docker-repo] # replace with your Docker Hub repo name
	docker buildx build --platform linux/amd64,linux/arm64 -t ${MY_REPO_NAME}/httpbin-mcp-server:latest --push .
	```

2. Run the container (make sure to set the environment variable):
	```bash
	docker run --rm -e HTTPBIN_HOST="https://httpbin.org" -p 8080:8080 ${MY_REPO_NAME}/httpbin-mcp-server:latest
	```

3. Verify the image contains the OpenTelemetry launcher and can start under the injected wrapper:
	```bash
	docker run --rm \
	  -e HTTPBIN_HOST="https://httpbin.org" \
	  -p 8080:8080 \
	  ${MY_REPO_NAME}/httpbin-mcp-server:latest \
	  sh -lc 'command -v opentelemetry-instrument && opentelemetry-instrument python main.py'
	```

	If kagent tracing is enabled, this is the execution path the controller will use for the container entrypoint.

## Example MCP Tool Invocation

To call the `httpbin_get` tool from an MCP client, send a request to the MCP server's `/mcp` endpoint with the appropriate payload. The server will respond with the result from the external HttpBin service.

```bsh
npx @modelcontextprotocol/inspector --log-level debug --server-url http://localhost:8080/mcp
```
