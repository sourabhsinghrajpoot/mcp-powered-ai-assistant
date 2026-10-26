from datetime import datetime, timezone
from mcp.server.fastmcp import FastMCP
mcp=FastMCP("assistant-demo")
@mcp.tool()
def get_current_time() -> str:
    """Return the current time in UTC."""
    return datetime.now(timezone.utc).isoformat()
@mcp.tool()
def calculate(operation:str, a:float, b:float) -> float:
    """Calculate using add, subtract, multiply, or divide."""
    if operation not in {'add','subtract','multiply','divide'}: raise ValueError('Unsupported operation')
    if operation=='divide' and b==0: raise ValueError('Cannot divide by zero')
    return {'add':a+b,'subtract':a-b,'multiply':a*b,'divide':a/b}[operation]
if __name__=='__main__': mcp.run(transport='stdio')
