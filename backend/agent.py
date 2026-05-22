import os
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters
from google.adk.tools.mcp_tool import StdioConnectionParams
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# Path to current directory to locate mcp_server.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MCP_SERVER_PATH = os.path.join(BASE_DIR, "mcp_server.py")

# Configure MCP Toolset with stdio transport to connect to mcp_server.py
mcp_toolset = MCPToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="python",
            args=[MCP_SERVER_PATH]
        )
    )
)

# System instruction for the agent
SYSTEM_INSTRUCTION = (
    "You are a GitHub profile analyst and dev card generator. "
    "When the user provides a GitHub username, you MUST actually invoke the tools (function calls) — "
    "do NOT describe, narrate, or print tool calls as text. "
    "Execute this exact sequence using real function calls:\n"
    "1) Invoke scrape_github(username=<username>).\n"
    "2) Invoke analyze_profile(github_data=<result of step 1>).\n"
    "3) Invoke generate_card_html(username=<username>, github_data=<step 1>, analysis=<step 2>).\n"
    "4) Invoke save_card(username=<username>, html=<result of step 3>).\n"
    "Never skip a step. Never output a step as text instead of a function call. "
    "After save_card completes, reply with a brief, enthusiastic confirmation message. "
    "If the profile is private or does not exist, say so clearly."
)

# Initialize the GitHub Card Agent
# Exporting as github_card_agent as requested
github_card_agent = LlmAgent(
    name="github_card_agent",
    model="gemini-2.5-flash",
    instruction=SYSTEM_INSTRUCTION,
    tools=[mcp_toolset],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.2,
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    ),
)
