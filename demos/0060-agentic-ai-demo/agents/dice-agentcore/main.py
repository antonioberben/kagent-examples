"""AgentCore Runtime entrypoint wrapping the dice ADK agent.

BedrockAgentCoreApp serves the AgentCore HTTP contract (POST /invocations,
GET /ping) on 0.0.0.0:8080. Each invocation runs the ADK agent with an
in-memory session and returns the final text response.
"""
import asyncio
import uuid

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from bedrock_agentcore.runtime import BedrockAgentCoreApp

from agent import root_agent

APP_NAME = "dice"
session_service = InMemorySessionService()
runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=session_service)


async def _run(query: str, user_id: str) -> str:
    session_id = str(uuid.uuid4())
    await session_service.create_session(app_name=APP_NAME, user_id=user_id, session_id=session_id)
    content = types.Content(role="user", parts=[types.Part(text=query)])
    final = ""
    async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
        if event.is_final_response() and event.content and event.content.parts:
            final = event.content.parts[0].text
    return final


app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload, context):
    prompt = payload.get("prompt", "Roll a 6-sided die and tell me if it is prime.")
    user_id = payload.get("user_id", "user")
    return {"result": asyncio.run(_run(prompt, user_id))}


if __name__ == "__main__":
    app.run()
