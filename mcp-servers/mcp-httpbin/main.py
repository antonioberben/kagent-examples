from fastmcp import FastMCP, Context
from fastmcp.server.dependencies import get_http_headers
import os
import requests
import logging
from typing import Optional # Added to use typing for POST data

logging.basicConfig(level=logging.INFO)

host = os.environ.get("HTTPBIN_HOST")
if not host:
    logging.critical("Missing required environment variable: HTTPBIN_HOST. This tool is configured to run a request against a HttpBin service. Exiting.")
    logging.shutdown()
    os._exit(1)

    

mcp = FastMCP("Minimal FastMCP server exposing simple tools.")

@mcp.tool()
async def httpbin_get(ctx: Context) -> dict:
    """Call the /get endpoint on HTTPBIN_HOST, propagating Authorization and baggage headers if present."""
    logging.info("Starting httpbin_get function")
    # Protect against host potentially being None just in case
    if not host:
        logging.critical("HTTPBIN_HOST environment variable is missing or empty at runtime.")
        raise RuntimeError("HTTPBIN_HOST environment variable is missing!")
    # Get all request headers
    forward_headers = get_headers()
    url = f"{host.rstrip('/')}/get"

    logging.info(f"Making request to URL: {url} with headers: {forward_headers}")
    response = requests.get(url, headers=forward_headers)
    logging.info("Received response with status code: %s", response.status_code)
    response.raise_for_status()
    result = response.json()
    logging.info("Successfully processed httpbin_get request")
    return result

@mcp.tool()
async def httpbin_post(ctx: Context, data: dict) -> dict:
    """Call the /post endpoint on HTTPBIN_HOST, sending the provided JSON data and propagating Authorization and baggage headers if present."""
    logging.info("Starting httpbin_post function")
    # Protect against host potentially being None just in case
    if not host:
        logging.critical("HTTPBIN_HOST environment variable is missing or empty at runtime.")
        raise RuntimeError("HTTPBIN_HOST environment variable is missing!")
    # Get all request headers
    forward_headers = get_headers()
    url = f"{host.rstrip('/')}/post"

    logging.info(f"Making request to URL: {url} with headers: {forward_headers} and data: {data}")
    # Use json=data to send the input dictionary as a JSON payload
    response = requests.post(url, headers=forward_headers, json=data)
    logging.info("Received response with status code: %s", response.status_code)
    response.raise_for_status()
    result = response.json()
    logging.info("Successfully processed httpbin_post request")
    return result


def get_headers():
    all_headers = get_http_headers(include_all=True)
    # Only pass Authorization, Baggage, and x-* headers if present
    forward_headers = {}
    if 'authorization' in all_headers and all_headers['authorization']:
        forward_headers['Authorization'] = all_headers['authorization']
    if 'baggage' in all_headers and all_headers['baggage']:
        forward_headers['Baggage'] = all_headers['baggage']
    # Include all x-* headers, case-insensitive
    for k, v in all_headers.items():
        if k.lower().startswith('x-') and v:
            # Preserve capitalization in outgoing request if desired
            forward_headers[k] = v
    logging.info(f"Forwarding selected headers: {forward_headers}")
    return forward_headers

if __name__ == "__main__":
    # Listen on 0.0.0.0 for external access
    mcp.run(transport="http", port=8080, host="0.0.0.0")