"""
Adapter for invoking LangChain-style tools robustly and normalizing responses.
Provides `invoke_tool(tool, payload)` which tries multiple call patterns
and returns a normalized dict: {"status": "ok"/"error", "result": {...}}.
"""
from typing import Any, Dict


def invoke_tool(tool: Any, payload: Any = None, mode: str = None, timeout: int = 30) -> Dict[str, Any]:
    """Invoke a tool with best-effort call patterns and normalize the response.

    - `tool` may be a plain callable, a LangChain `@tool` function, or an object exposing `.run` or `.func`.
    - `payload` may be a string, dict or other object depending on tool signature.

    Returns dict: {"status": "ok", "result": <dict|string|raw>} or {"status":"error","error":"..."}
    """
    # Prepare candidate call arguments
    try:
        # If payload is a dict and includes 'transcript' and mode key, keep as-is
        # Candidate invocations will try sensible permutations
        candidates = []
        if payload is None:
            candidates.append(())
            candidates.append(({"mode": mode},))
        else:
            # If payload is already a dict, try passing it as kwargs and as sole positional arg
            if isinstance(payload, dict):
                candidates.append((payload,))
                candidates.append((payload.get('transcript'),))
                candidates.append((payload.get('transcript'), payload.get('mode')))
                candidates.append((payload.get('transcript'),))
                candidates.append((payload,))
            else:
                candidates.append((payload,))
                candidates.append((payload, mode))
                candidates.append(({ 'transcript': payload, 'mode': mode },))

        last_err = None
        for args in candidates:
            try:
                # Try direct callable
                if callable(tool):
                    try:
                        res = tool(*args)
                    except TypeError:
                        # try passing as kwargs if single dict
                        if len(args) == 1 and isinstance(args[0], dict):
                            res = tool(**args[0])
                        else:
                            raise
                    return {"status": "ok", "result": res}

                # Try .run
                if hasattr(tool, 'run'):
                    try:
                        res = tool.run(*args)
                        return {"status": "ok", "result": res}
                    except TypeError:
                        if len(args) == 1 and isinstance(args[0], dict):
                            res = tool.run(**args[0])
                            return {"status": "ok", "result": res}
                        raise

                # Try .func
                if hasattr(tool, 'func'):
                    try:
                        res = tool.func(*args)
                        return {"status": "ok", "result": res}
                    except TypeError:
                        if len(args) == 1 and isinstance(args[0], dict):
                            res = tool.func(**args[0])
                            return {"status": "ok", "result": res}
                        raise

            except Exception as e:
                last_err = e
                continue

        # If we reach here, nothing worked
        err_msg = f"Tool invocation failed for all tried signatures. Last error: {last_err}"
        return {"status": "error", "error": err_msg}

    except Exception as e:
        return {"status": "error", "error": str(e)}
