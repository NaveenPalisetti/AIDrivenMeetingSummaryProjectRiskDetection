"""
Agent-to-Agent (A2A) communication utilities and decorators for MCP.
"""
from typing import Callable, Any, Dict
from functools import wraps

def a2a_endpoint(func: Callable) -> Callable:
    """Decorator for logging and error handling of A2A endpoints."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        print(f"[A2A] Calling {func.__name__}")
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"[A2A] Error in {func.__name__}: {e}")
            return {"status": "error", "error": str(e)}
    return wrapper

def a2a_request(agent_func: Callable, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Standardized request/response pattern for A2A calls."""
    try:
        response = agent_func(**payload)
        return {"status": "ok", "result": response}
    except Exception as e:
        print(f"[A2A] Request error: {e}")
        return {"status": "error", "error": str(e)}

# Add more A2A protocol helpers as needed
