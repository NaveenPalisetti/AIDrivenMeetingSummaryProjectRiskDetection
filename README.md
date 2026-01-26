

# AI-Driven Meeting Summary & Project Risk Detection

## Overview
This project is a production-ready, modular multi-agent system for meeting summarization, project risk detection, and task management. It leverages local language models (BART, Mistral), orchestrates agents for summarization, risk detection, task extraction, calendar integration, and notifications, and provides a modern Streamlit UI for interactive workflows. The backend is built with FastAPI, LangChain, and LangGraph.

## Features
- **Meeting Summarization:** Extracts concise summaries and action items from transcripts using BART or Mistral models.
- **Risk Detection:** Identifies project risks from meeting content and Jira issues.
- **Task Extraction:** Finds and tracks action items and tasks.
- **Calendar Integration:** Fetches events and meeting data from Google Calendar.
- **Jira Integration:** Creates Jira issues for selected action items.
- **Notifications:** Sends reminders and alerts to users via Slack or console.
- **Modular Multi-Agent Orchestration:** All agents are orchestrated via LangChain/LangGraph workflows.
- **Local Model Support:** No external API calls; all models run locally for privacy and speed.

## Architecture
The system consists of:
- **Backend API:** FastAPI server exposing endpoints for summarization and orchestration.
- **Streamlit UI:** Interactive web app for users to trigger workflows, view results, and manage meetings.
- **Agents:** Modular Python classes for summarization, risk detection, task management, calendar, Jira, and notifications.
- **Workflow Graph:** LangGraph-based workflow for chaining agent actions.
- **Data Layer:** Local storage for transcripts, summaries, and configuration.

See `PROJECT_STRUCTURE.md` for a detailed breakdown of the codebase.

## Setup & Configuration
1. **Clone the repository**
2. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```
3. **Download/Place local models:**
   - Place BART and Mistral models in the `models/` directory, or set `BART_MODEL_PATH`/`MISTRAL_MODEL_PATH` as environment variables.
4. **Configure credentials:**
   - Add API keys and credentials to `mcp/config/credentials.json` (for Google Calendar, Jira, etc.).
   - For Slack notifications, create a Slack Incoming Webhook and set the environment variable `SLACK_WEBHOOK_URL`.
5. **Environment variables:**
   - Copy `.env.example` to `.env` and update as needed.

## Running the System

### Development (Local)
- **Start the backend API:**
  ```sh
  uvicorn mcp.server.mcp_api:app --reload
  ```
- **Start the Streamlit UI:**
  ```sh
  streamlit run orchestrator_streamlit_client.py
  ```

### Docker (Recommended for Production)
Build and run both services in containers:
```sh
docker build -t meeting-orchestrator .
docker run --rm -p 8000:8000 -p 8501:8501 --env-file .env meeting-orchestrator
```
Or use Docker Compose for multi-container orchestration.

### Production Best Practices
- Use a process manager (e.g., systemd, supervisord, or Docker Compose) to run the FastAPI backend and Streamlit UI as separate services.
- Set all secrets and environment variables securely (never hardcode in code or commit to git).
- Use HTTPS and proper authentication for public deployments.
- Monitor logs and set up alerting for errors or failed notifications.
- Regularly update dependencies and rotate credentials.

## Workflow Stages
The orchestrator logic follows these stages:
1. **fetch:** Fetch recent calendar events and transcripts.
2. **preprocess:** Clean and chunk transcripts for summarization.
3. **summarize:** Summarize meetings and extract action items (BART or Mistral).
4. **jira:** Create Jira issues for selected action items (if enabled/configured).
5. **risk:** Detect risks from both meeting summary and live Jira issues.
6. **notify:** Send notifications (console and/or Slack) with summary, tasks, and risks.

Each stage is triggered by the UI or API, and results are displayed in the Streamlit app.

## Customization & Extensibility
- Add new agents/tools in `mcp/agents/` and register them in the workflow.
- Update UI components in `mcp/ui/` for new features.
- Extend risk detection, summarization, or notification logic as needed.
- Update the workflow graph in `mcp/agents/meeting_workflow_graph.py` to change orchestration.

## Testing
Run tests with:
```sh
pytest
```

## Security & Secrets
- Do NOT commit secrets to the repository.
- Add your credentials locally to `mcp/config/credentials.json` (this file is ignored by `.gitignore`) or use environment variables as shown in `.env.example`.
- Rotate any credentials that were previously exposed.

## License
MIT License
