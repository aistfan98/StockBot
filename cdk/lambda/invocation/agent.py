import os
from strands import Agent
from strands.tools.mcp import MCPClient
from mcp import stdio_client, StdioServerParameters

# Model configuration - exported for use in logging/storage
MODEL_USED = "global.anthropic.claude-opus-4-6-v1"

stockbot_mcp_client = MCPClient(lambda: stdio_client(
    StdioServerParameters(
        command="python3",
        args=["tools.py"],
        env=os.environ.copy()
    )
))

def invoke_agent(prompt):
    with stockbot_mcp_client:
        tools = stockbot_mcp_client.list_tools_sync()
        agent = Agent(tools=tools, model=MODEL_USED)

        return agent(prompt)