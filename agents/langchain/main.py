import os
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi import WebSocket, WebSocketDisconnect
from contextlib import asynccontextmanager
import uvicorn
import logging
import json

# --- LangChain Core Components ---
from langchain.agents import create_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import Tool

# --- MCP Adapter for Dynamic Tool Discovery ---
from langchain_mcp_adapters.client import MultiServerMCPClient

load_dotenv()

# Logging
logger = logging.getLogger(__name__)
logging.basicConfig(format="[%(levelname)s]: %(message)s", level=logging.INFO)

mcp_server_url = os.getenv("MCP_SERVER")
SYSTEM_INSTRUCTION = os.getenv(
    "SYSTEM_INSTRUCTION",
    "You are a specialized assistant for currency conversions. "
    "Your sole purpose is to use the 'get_exchange_rate' tool to answer questions about currency exchange rates. "
    "If the user asks about anything other than currency conversion or exchange rates, "
    "politely state that you cannot help with that topic and can only assist with currency-related queries. "
    "Do not attempt to answer unrelated questions or use tools for other purposes."
)
llm_model = os.getenv("LLM_MODEL", "gpt-3.5-turbo-0125")
llm_api_base = os.getenv("LLM_API_BASE", "https://api.openai.com/v1")
llm_api_key = os.getenv("LLM_API_KEY", "")

# Build kwargs for ChatOpenAI only including optional keys when set
llm_kwargs = {"model": llm_model, "temperature": 0}
if llm_api_base:
    llm_kwargs["openai_api_base"] = llm_api_base
if llm_api_key:
    llm_kwargs["openai_api_key"] = llm_api_key

llm = ChatOpenAI(**llm_kwargs)

def check_credentials():
    """Return None if credentials ok, otherwise raise helpful HTTPException."""
    # If MCP server is configured we can operate without an LLM key
    if mcp_server_url:
        return
    # Otherwise we require an LLM API key
    if not llm_api_key:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "No LLM API key configured. Set LLM_API_KEY in environment or .env.",
                "how_to_fix": "export LLM_API_KEY=sk-... or add LLM_API_KEY=sk-... to your .env",
            },
        )

async def discover_tools() -> list[Tool]:
    if not mcp_server_url:
        return []
    mcp_config = {
        "remote_server": {
            "url": mcp_server_url,
            "transport": "streamable_http",
        }
    }
    client = MultiServerMCPClient(mcp_config)
    try:
        tools = await client.get_tools()
        return tools
    except Exception:
        logger.error("Error during MCP tool discovery", exc_info=True)
        return []


# Cached MCP discovery state (populated at startup)
cached_tools: list[Tool] = []
mcp_initialized = False
mcp_toolset_available = False


async def startup_discover():
    """Attempt to discover tools at startup and cache them for API endpoints."""
    global cached_tools, mcp_initialized, mcp_toolset_available
    if not mcp_server_url:
        mcp_initialized = False
        mcp_toolset_available = False
        cached_tools = []
        logger.info("No MCP_SERVER configured; skipping tool discovery.")
        return
    
    try:
        tools = await discover_tools()
        cached_tools = tools or []
        mcp_initialized = True
        mcp_toolset_available = len(cached_tools) > 0
        
        # --- START OF NEW LOGIC ---
        if mcp_toolset_available:
            tool_names = [getattr(t, 'name', 'Unknown') for t in cached_tools]
            logger.info("✅ Startup: Discovered %d MCP tools: %s", len(cached_tools), tool_names)
        else:
            logger.warning("⚠️ Startup: MCP_SERVER configured, but **no tools were discovered**.")
        # --- END OF NEW LOGIC ---
        
    except Exception as e:
        mcp_initialized = True
        mcp_toolset_available = False
        cached_tools = []
        logger.exception("❌ Error discovering MCP tools at startup: %s", e)   

@asynccontextmanager
async def lifespan(app: FastAPI):
    # perform startup discovery
    await startup_discover()
    try:
        yield
    finally:
        # no special shutdown actions
        return


# create FastAPI app with lifespan handler
app = FastAPI(lifespan=lifespan)

async def ask_currency_agent(query: str):
    # CORRECTED: Use the globally cached tools instead of re-discovering them
    tools = cached_tools
    
    if not tools:
        # Fallback to direct LLM call using message objects
        logger.info("LLM request: %s", query)
        sys_msg = SystemMessage(content=SYSTEM_INSTRUCTION)
        human_msg = HumanMessage(content=query)
        # ChatOpenAI provides async invocation via `ainvoke` accepting messages
        resp = await llm.ainvoke([sys_msg, human_msg])
        # `resp` is typically an AIMessage or a ModelResponse; try to extract text
        try:
            text = getattr(resp, "content", str(resp))
            logger.info("LLM response: %s", text)
            return text
        except Exception:
            logger.info("LLM response (raw): %s", str(resp))
            return str(resp)
            
    # Create an agent graph compatible with installed LangChain
    # create_agent accepts a model (Chat model or model string), tools, and system prompt
    logger.info("Agent graph request (query): %s", query)
    graph = create_agent(model=llm, tools=tools, system_prompt=SYSTEM_INSTRUCTION)

    # The compiled graph exposes async invocation via `ainvoke`. It expects
    # inputs in the form {"messages": [{"role": "user", "content": ...}]}
    inputs = {"messages": [{"role": "user", "content": query}]}
    result = await graph.ainvoke(inputs)
    try:
        logger.info("Agent graph response: %s", json.dumps(result, default=str))
    except Exception:
        logger.info("Agent graph response (raw): %s", str(result))

    # `result` is typically a dict or object containing messages/result.
    # For compatibility, try to extract content from returned structure.
    try:
        # If result is a mapping with 'messages' or 'result'
        if isinstance(result, dict):
            if "output" in result:
                return result["output"]
            if "messages" in result:
                msgs = result["messages"]
                if msgs:
                    return getattr(msgs[-1], "content", str(msgs[-1]))
        # Fallback: return the result string representation
        return str(result)
    except Exception:
        return str(result)
# --- FastAPI Server Setup ---


@app.websocket("/agent/ws")
async def agent_ws(websocket: WebSocket):
    """WebSocket endpoint for long-lived sessions and streaming responses.

    Protocol (JSON messages):
    - Client -> Server: {"type":"start", "query": "..."}
    - Server -> Client: multiple {"type":"chunk", "data": "..."} messages
    - Server -> Client: final {"type":"done"}
    """
    await websocket.accept()
    try:
        while True:
            msg = await websocket.receive_text()
            try:
                data = json.loads(msg)
            except Exception:
                await websocket.send_text(json.dumps({"type": "error", "message": "invalid json"}))
                continue

            if data.get("type") != "start":
                await websocket.send_text(json.dumps({"type": "error", "message": "unsupported message type"}))
                continue

            query = data.get("query", "")
            if not query:
                await websocket.send_text(json.dumps({"type": "error", "message": "missing query"}))
                continue

            # discover tools for this session
            tools = await discover_tools()

            # create a fresh agent graph for this websocket session
            graph = create_agent(model=llm, tools=tools, system_prompt=SYSTEM_INSTRUCTION)

            # prepare inputs and stream
            inputs = {"messages": [{"role": "user", "content": query}]}

            try:
                async for chunk in graph.astream(inputs):
                    # send each chunk to the client
                    chunk_text = str(chunk)
                    logger.info("Streaming chunk: %s", chunk_text)
                    await websocket.send_text(json.dumps({"type": "chunk", "data": chunk_text}))
            except Exception as e:
                await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))
            await websocket.send_text(json.dumps({"type": "done"}))

    except WebSocketDisconnect:
        return


@app.post("/invoke")
@app.post("/agent/invoke")
async def invoke(request: Request):
    # Accept multiple request formats safely:
    # 1) JSON body: {"query": "..."}
    # 2) form-encoded: query=...
    # 3) raw text body containing the query
    # 4) query parameter: /agent/invoke?query=...
    query = None
    try:
        data = await request.json()
        if isinstance(data, dict):
            query = data.get("query")
    except Exception:
        # ignore JSON errors (empty body or invalid JSON)
        data = None

    # form or query params
    if not query:
        form = await request.form() if request.headers.get("content-type", "").startswith("application/x-www-form-urlencoded") else None
        if form and "query" in form:
            query = form["query"]

    # raw body
    if not query:
        body = await request.body()
        if body:
            try:
                query_text = body.decode("utf-8")
            except Exception:
                query_text = None
            if query_text:
                # if body contains JSON-like content, try to parse
                if query_text.strip().startswith("{"):
                    try:
                        import json

                        parsed = json.loads(query_text)
                        if isinstance(parsed, dict) and "query" in parsed:
                            query = parsed.get("query")
                    except Exception:
                        pass
                # otherwise treat body as raw query text
                if not query:
                    query = query_text.strip()

    # query param
    if not query:
        query = request.query_params.get("query")

    if not query:
        return JSONResponse({"error": "Missing 'query' field."}, status_code=400)
    # Validate credentials / environment before invoking LLM
    try:
        check_credentials()
    except HTTPException as e:
        return JSONResponse({"error": e.detail}, status_code=e.status_code)

    result = await ask_currency_agent(query)
    usage = {"events": 1}
    return JSONResponse({"content": result, "usage": usage}, status_code=200)


@app.post("/api/agent/invoke")
async def api_agent_invoke(request: Request):
    """API endpoint expected by the frontend. Returns a consistent JSON shape.

    Request JSON: { messages: [{role,content,timestamp?}, ...], max_tokens?, temperature?, mode? }
    Response on success: { content: "...", usage: {...} }
    Error: { error: "human message", detail: "...", status_code: 400 }
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body", "detail": "Request body must be JSON", "status_code": 400}, status_code=400)

    messages = body.get("messages")
    if not messages or not isinstance(messages, list):
        return JSONResponse({"error": "Missing 'messages'","detail": "The 'messages' array must contain at least one message","status_code": 400}, status_code=400)

    max_tokens = body.get("max_tokens")
    temperature = body.get("temperature")
    mode = body.get("mode")

    # Build per-request LLM kwargs
    llm_req_kwargs = {"model": llm_model}
    if temperature is not None:
        llm_req_kwargs["temperature"] = temperature
    else:
        llm_req_kwargs["temperature"] = llm_kwargs.get("temperature", 0)
    if llm_api_base:
        llm_req_kwargs["openai_api_base"] = llm_api_base
    if llm_api_key:
        llm_req_kwargs["openai_api_key"] = llm_api_key
    if max_tokens is not None:
        llm_req_kwargs["max_tokens"] = max_tokens

    # Create a per-request LLM instance when parameters differ
    try:
        llm_req = ChatOpenAI(**llm_req_kwargs)
    except Exception:
        llm_req = llm

    # Convert frontend messages to graph-compatible dicts and message objects
    msgs_for_graph = []
    msgs_for_llm = []
    system_prompt_found = False
    for m in messages:
        role = m.get("role")
        content = m.get("content", "")
        msgs_for_graph.append({"role": role, "content": content})
        if role == "system":
            msgs_for_llm.append(SystemMessage(content=content))
            system_prompt_found = True
        elif role == "user":
            msgs_for_llm.append(HumanMessage(content=content))
        elif role == "assistant":
            msgs_for_llm.append(AIMessage(content=content))
        else:
            msgs_for_llm.append(HumanMessage(content=content))

    # Determine whether to use tools (MCP) - prefer cached_tools discovered at startup
    tools = cached_tools if cached_tools else []

    try:
        if tools:
            # Use agent graph with tools
            sys_prompt = None
            if not system_prompt_found:
                sys_prompt = SYSTEM_INSTRUCTION
            else:
                sys_prompt = None
            graph = create_agent(model=llm_req, tools=tools, system_prompt=sys_prompt or SYSTEM_INSTRUCTION)
            inputs = {"messages": msgs_for_graph}
            result = await graph.ainvoke(inputs)
            # extract content
            content = None
            if isinstance(result, dict):
                if "output" in result:
                    content = result["output"]
                elif "messages" in result and result["messages"]:
                    last = result["messages"][-1]
                    content = getattr(last, "content", str(last))
            if content is None:
                content = str(result)
        else:
            # LLM-only path
            logger.info("LLM request (api): %s", msgs_for_graph)
            resp = await llm_req.ainvoke(msgs_for_llm)
            content = getattr(resp, "content", str(resp))
            logger.info("LLM response (api): %s", content)

        usage = {
            "events": 1,
            "session_id": body.get("session_id"),
            "user_id": body.get("user_id"),
        }

        return JSONResponse({"content": content, "usage": usage}, status_code=200)
    except Exception as e:
        logger.exception("Error handling API invoke")
        return JSONResponse({"error": "Internal server error", "detail": str(e), "status_code": 500}, status_code=500)


@app.get("/api/health")
async def api_health():
    return JSONResponse({
        "status": "ok",
        "api_key_configured": bool(llm_api_key),
        "mcp_server": mcp_server_url,
        "mcp_initialized": mcp_initialized,
        "mcp_toolset_available": mcp_toolset_available,
    })


@app.get("/api/tools")
async def api_tools():
    tools_list = []
    for t in cached_tools:
        try:
            name = getattr(t, "name", None) or t.get("name") if isinstance(t, dict) else str(t)
            desc = getattr(t, "description", None) or t.get("description") if isinstance(t, dict) else ""
            input_schema = {}
            # try common schema attributes
            input_schema = getattr(t, "args_schema", None) or getattr(t, "input_schema", None) or {}
            tools_list.append({"name": name, "description": desc, "input_schema": input_schema})
        except Exception:
            tools_list.append({"name": str(t), "description": "", "input_schema": {}})
    return JSONResponse({"tools": tools_list})


@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)