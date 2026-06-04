"""Dice agent (Google ADK) — same roll_die/check_prime logic as agents/dice,
without the kagent MCP wiring, so it can be wrapped by the AgentCore runtime SDK."""
import random

from google.adk import Agent
from google.adk.tools.tool_context import ToolContext
from google.adk.models.lite_llm import LiteLlm


def roll_die(sides: int, tool_context: ToolContext) -> int:
    """Roll a die and record the outcome for later reference."""
    result = random.randint(1, sides)
    if "rolls" not in tool_context.state:
        tool_context.state["rolls"] = []
    tool_context.state["rolls"] = tool_context.state["rolls"] + [result]
    return result


async def check_prime(nums: list[int]) -> str:
    """Check whether the provided numbers are prime."""
    primes = set()
    for number in nums:
        number = int(number)
        if number <= 1:
            continue
        is_prime = True
        for i in range(2, int(number**0.5) + 1):
            if number % i == 0:
                is_prime = False
                break
        if is_prime:
            primes.add(number)
    return "No prime numbers found." if not primes else f"{', '.join(str(num) for num in primes)} are prime numbers."


def create_model():
    """OpenAI model via LiteLLM. Reads OPENAI_API_KEY from the environment."""
    return LiteLlm(model="openai/gpt-4o-mini")


root_agent = Agent(
    model=create_model(),
    name="dice_agent",
    description="Dice roller + prime checker demo agent (AgentCore runtime)",
    instruction="""
You roll dice and answer questions about the outcome of the dice rolls.
You can roll dice of different sizes and use multiple tools in parallel.
When asked to roll a die, call roll_die with an integer number of sides. Never roll on your own.
When checking primes, call check_prime with a list of integers.
When asked to roll and check primes: first call roll_die, wait for the result, then call check_prime with that result, and always include the roll result in your response.
""",
    tools=[roll_die, check_prime],
)
