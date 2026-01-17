
# AI-Driven Meeting Summary & Project Risk Detection

## Overview
This project is a production-ready, multi-agent assistant for meetings and project management. It uses local language models (BART, Mistral) and orchestrates agents for summarization, risk detection, task extraction, calendar integration, and notifications. The system is built with LangChain, LangGraph, and Streamlit for a chat-driven UI.

## Features
- **Meeting Summarization:** Extracts concise summaries and action items from transcripts using BART or Mistral models.
- **Risk Detection:** Identifies project risks from meeting content.
- **Task Extraction:** Finds and tracks action items and tasks.
- **Calendar Integration:** Fetches events and meeting data.
- **Notifications:** Sends reminders and alerts to users.
- **Modular Multi-Agent Orchestration:** All agents are orchestrated via LangChain/LangGraph workflows.
- **Local Model Support:** No external API calls; all models run locally.

## Project Structure
See `PROJECT_STRUCTURE.md` for a detailed breakdown.

Key folders:
- `mcp/agents/` — Agent logic and LangChain/LangGraph tools
- `mcp/tools/` — Standalone tools/utilities
- `mcp/core/` — Core framework and protocols
- `mcp/server/` — API/backend
- `mcp/ui/` — Streamlit UI components
- `models/` — Local model files

## Setup
1. **Clone the repository**
2. **Install dependencies:**
	 ```sh
	 pip install -r requirements.txt
	 ```
3. **Download/Place local models:**
	 - Place BART and Mistral models in the `models/` directory as described in the code or set environment variables `BART_MODEL_PATH` and `MISTRAL_MODEL_PATH`.
4. **Configure credentials:**
	 - Add any required API keys or credentials to `mcp/config/credentials.json` (for calendar, etc.)

## Usage
- **Run the Streamlit UI:**
	```sh
	streamlit run orchestrator_streamlit_client.py
	```
- **Run the backend API (if needed):**
	```sh
	uvicorn mcp.server.mcp_api:app --reload
	```

## Extending the System
- Add new agents/tools in `mcp/agents/` and register them in the workflow graph.
- Update the LangGraph workflow in `mcp/agents/meeting_workflow_graph.py` to change orchestration.
- UI components can be extended in `mcp/ui/`.

## Testing
- Run tests with:
	```sh
	pytest
	```

## Authors
- [Your Name]

## License
MIT License

## Security & Secrets
- This repository previously contained sensitive credentials. Those have been sanitized. Do NOT commit secrets to the repository.
- Add your credentials locally to `mcp/config/credentials.json` (this file is ignored by `.gitignore`) or use environment variables as shown in `.env.example`.
- Rotate any credentials that were previously exposed.

## Docker (optional)
A basic `Dockerfile` is included for local development. It installs dependencies and runs both the FastAPI backend and the Streamlit UI for convenience. For production, run services separately and use proper process supervision.

Build and run locally (dev):
```sh
docker build -t meeting-orchestrator .
docker run --rm -p 8000:8000 -p 8501:8501 --env-file .env meeting-orchestrator
```

## Environment & Models
- For reproducible runs, set model paths in `.env` or use environment variables `BART_MODEL_PATH` and `MISTRAL_MODEL_PATH`.
- To enable Mistral (requires GPU and local model), set `MISTRAL_ENABLED=1` and provide `MISTRAL_MODEL_PATH`.
