from mcp.client.mcp_client import MCPClient

def send_notification(message, metadata=None):
    """
    Send a notification using the MCP notification agent.
    Args:
        message (str): The message to send.
        metadata (dict, optional): Additional metadata for the notification.
    Returns:
        dict: The response from the notification agent.
    """
    mcp = MCPClient()
    payload = {"message": message}
    meta = metadata or {}
    return mcp.notify({"message": message, **meta})

# Example usage:
if __name__ == "__main__":
    resp = send_notification("Test notification from MCP notification tool.")
    print(resp)
