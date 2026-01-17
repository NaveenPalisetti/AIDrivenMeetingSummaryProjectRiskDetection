# Project Structure and Naming Conventions

This project follows a modular, production-grade structure for a multi-agent meeting assistant using LangChain, LangGraph, and local models.

## Folder Structure

- `mcp/agents/` — All agent logic and LangChain/LangGraph tools (summarization, calendar, risk, task, notification, etc.)
- `mcp/tools/` — Standalone tools/utilities (e.g., notification, summarization)
- `mcp/core/` — Core framework, context, and protocol logic (MCP, A2A, utils)
- `mcp/server/` — API/backend server code (e.g., FastAPI)
- `mcp/ui/` — UI components (e.g., Streamlit chat UI)
- `mcp/config/` — Configuration and credentials
- `mcp/data/` — Data storage (summaries, tasks)
- `models/` — Local model files (BART, Mistral, etc.)
- `scripts/` — Scripts/utilities (optional, for future use)

## Naming Conventions

- Python files: `snake_case.py`
- Classes: `CamelCase`
- Functions: `snake_case`
- Tools/agents: Suffix with `_agent.py` or `_tool.py` as appropriate
- Config/data: Use descriptive names (e.g., `credentials.json`, `tasks.json`)

## Best Practices

- Keep agent/tool logic modular and reusable
- Separate UI, API, and core logic
- Store models and data outside of code directories
- Use requirements.txt for dependencies
- Add docstrings and comments for clarity

---

This structure is scalable and maintainable for production use. Update as needed for new agents, tools, or features.
