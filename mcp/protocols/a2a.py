"""
Agent-to-Agent (A2A) communication utilities and decorators for MCP.
"""
from typing import Callable, Any, Dict
from functools import wraps

def a2a_endpoint(func: Callable) -> Callable:
    """Decorator for logging and error handling of A2A endpoints."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        print(f"[A2A] ENTER endpoint: {func.__name__}")
        print(f"[A2A] Args: {args}")
        #print(f"[A2A] Kwargs: {kwargs}")
        try:
            result = func(*args, **kwargs)
            print(f"[A2A] EXIT endpoint: {func.__name__} -> result")
            return result
        except Exception as e:
            print(f"[A2A] ERROR in endpoint {func.__name__}: {e}")
            raise
    return wrapper

def a2a_request(agent_func: Callable, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Standardized request/response pattern for A2A calls."""
    payload_str = str(payload)
    print(f"[A2A] REQUEST to {getattr(agent_func, '__name__', str(agent_func))} with payload: {payload_str[:100]}{'...' if len(payload_str) > 100 else 'payload taken'}")
    try:
        result = agent_func(**payload)
        result_str = str(result)
        print(f"[A2A] RESPONSE from {getattr(agent_func, '__name__', str(agent_func))}: {result_str[:100]}{'...' if len(result_str) > 100 else ''}")
        return {"status": "ok", "result": result}
    except Exception as e:
        print(f"[A2A] ERROR in request to {getattr(agent_func, '__name__', str(agent_func))}: {e}")
        return {"status": "error", "error": str(e)}

# Add more A2A protocol helpers as needed
