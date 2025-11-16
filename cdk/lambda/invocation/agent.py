from strands import Agent
from strands.tools.mcp import MCPClient
from mcp import stdio_client, StdioServerParameters

stockbot_mcp_client = MCPClient(lambda: stdio_client(
    StdioServerParameters(
        command="python3",
        args=["tools.py"]
    )
))

def invoke_agent(prompt):
    with stockbot_mcp_client:
        tools = stockbot_mcp_client.list_tools_sync()
        agent = Agent(tools=tools)

        return agent(prompt)