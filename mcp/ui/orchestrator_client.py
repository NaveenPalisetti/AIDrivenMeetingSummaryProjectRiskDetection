"""
Lightweight orchestrator HTTP client helpers for Streamlit UI.
Keep network/io logic out of the main Streamlit file for testability.
"""
from typing import Any, Dict
import requests


def call_orchestrator(api_url: str, payload: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
    """Call the orchestrator HTTP API and return parsed JSON on success.

    Raises RuntimeError on non-200 responses or requests exceptions.
    """
    try:
        resp = requests.post(api_url, json=payload, timeout=timeout)
    except Exception as e:
        raise RuntimeError(f"Request failed: {e}")
    if resp.status_code != 200:
        raise RuntimeError(f"API Error: {resp.status_code} {resp.text}")
    try:
        return resp.json()
    except Exception as e:
        # Return raw text as fallback
        return {"raw_text": resp.text}
