
try:
    from mcp.client.mcp_client import MCPClient
except ImportError:
    MCPClient = None


def send_notification(message, metadata=None):
    """
    Send a notification using the MCP notification agent.
    Args:
        message (str): The message to send.
        metadata (dict, optional): Additional metadata for the notification.
    Returns:
        dict: The response from the notification agent, or None if MCPClient is unavailable.
    """
    if MCPClient is None:
        print("[WARN] MCPClient not available: mcp.client.mcp_client could not be imported. Notification skipped.")
        return None
    mcp = MCPClient()
    payload = {"message": message}
    meta = metadata or {}
    return mcp.notify({"message": message, **meta})

# Example usage:
if __name__ == "__main__":
    resp = send_notification("Test notification from MCP notification tool.")
    print(resp)
