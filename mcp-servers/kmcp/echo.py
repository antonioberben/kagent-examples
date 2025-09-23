"""Echo tool for MCP server.
"""
import os
from core.server import mcp
from core.utils import get_tool_config


@mcp.tool()
def echo(message: str) -> str:
    """Echo tool implementation.

    This tool returns a static message

    Args:
        message: Input message

    Returns:
        str: Result of the tool operation
    """
    # Get tool-specific configuration from kmcp.yaml
    config = get_tool_config("echo")

    # get environment variable if exists with name MESSAGE and defaul value "default"
    message = os.getenv("MESSAGE", "This is the echo message from environment variable!")

    # Example: Basic text processing
    prefix = config.get("prefix", "echo: ")
    return f"{prefix}{message}"
