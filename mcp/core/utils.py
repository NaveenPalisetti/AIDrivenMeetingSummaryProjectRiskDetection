import uuid

def gen_id(prefix: str = "id") -> str:
    """Generate a unique ID with a given prefix."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"
