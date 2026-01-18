
## Production-Ready Workflow Overview

### 1. Setup & Configuration (One-Time)

1. **Clone the repository**
2. **Install dependencies:**
	 ```sh
	 pip install -r requirements.txt
	 ```
3. **Download/Place local models:**
	 - Place BART and Mistral models in the `models/` directory, or set `BART_MODEL_PATH`/`MISTRAL_MODEL_PATH` as environment variables.
4. **Configure credentials:**
	 - Add API keys and credentials to `mcp/config/credentials.json` (for Google Calendar, Jira, etc.).
	 - For Slack notifications, create a Slack Incoming Webhook (see below) and set the environment variable `SLACK_WEBHOOK_URL` to your webhook URL.

### 2. Running the System (Development & Production)

#### Development (Local)
- **Start the backend API:**
	```sh
	uvicorn mcp.server.mcp_api:app --reload
	```
- **Start the Streamlit UI:**
	```sh
	streamlit run orchestrator_streamlit_client.py
	```

#### Production Best Practices
- Use a process manager (e.g., systemd, supervisord, or Docker Compose) to run the FastAPI backend and Streamlit UI as separate services.
- Set all secrets and environment variables securely (never hardcode in code or commit to git).
- Use HTTPS and proper authentication for public deployments.
- Monitor logs and set up alerting for errors or failed notifications.
- Regularly update dependencies and rotate credentials.

#### Docker (Recommended for Production)
Build and run both services in containers:
```sh
docker build -t meeting-orchestrator .
docker run --rm -p 8000:8000 -p 8501:8501 --env-file .env meeting-orchestrator
```
Or use Docker Compose for multi-container orchestration.

### 3. Workflow Stages (Orchestrator Logic)

1. **fetch**: Fetch recent calendar events and transcripts.
2. **preprocess**: Clean and chunk transcripts for summarization.
3. **summarize**: Summarize meetings and extract action items (BART or Mistral).
4. **jira**: Create Jira issues for selected action items (if enabled/configured).
5. **risk**: Detect risks from both meeting summary and live Jira issues.
6. **notify**: Send notifications (console and/or Slack) with summary, tasks, and risks.

Each stage is triggered by the UI or API, and results are displayed in the Streamlit app.

### 4. Slack Notification Setup

To enable Slack notifications:
1. Go to https://api.slack.com/apps and create a new app.
2. Add the "Incoming Webhooks" feature and activate it.
3. Create a new webhook for your desired channel and copy the URL.
4. Set the environment variable:
	 ```sh
	 set SLACK_WEBHOOK_URL=your_webhook_url_here
	 ```
5. Restart your app. Notifications will now be sent to Slack when the notify stage runs.

### 5. Customization & Extensibility

- Add new agents/tools in `mcp/agents/` and register them in the workflow.
- Update UI components in `mcp/ui/` for new features.
- Extend risk detection, summarization, or notification logic as needed.

---

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
