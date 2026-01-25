import os
from strands import Agent
from strands.tools.mcp import MCPClient
from mcp import stdio_client, StdioServerParameters

# Model configuration - exported for use in logging/storage
MODEL_USED = "global.anthropic.claude-sonnet-4-5-20250929-v1:0"

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