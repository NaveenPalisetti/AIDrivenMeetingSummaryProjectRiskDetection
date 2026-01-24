# MCP API for summarization (mcep_api.py)
from fastapi import FastAPI
from pydantic import BaseModel

from mcp.core.mcp import MCPHost
from mcp.tools.summarization_tool import SummarizationTool
from mcp.agents.orchestrator_agent import OrchestratorAgent


app = FastAPI()
mcp_host = MCPHost()
summ_tool = SummarizationTool()
mcp_host.register_tool(summ_tool)
orchestrator = OrchestratorAgent()


class TranscriptIn(BaseModel):
    transcript: str
    meeting_id: str = "ui_session"

class OrchestratorIn(BaseModel):
    query: str
    selected_event_indices: list = None
    mode: str = None
    processed_transcripts: list = None
    selected_action_items: list = None


@app.post("/mcp/summarize")
async def summarize(transcript_in: TranscriptIn):
    session_id = mcp_host.create_session(agent_id="ui_agent")
    params = {"transcript": transcript_in.transcript, "meeting_id": transcript_in.meeting_id}
    result = await mcp_host.execute_tool(session_id, tool_id="summarization", parameters=params)
    mcp_host.end_session(session_id)
    return result

# New endpoint for orchestrator agent
@app.post("/mcp/orchestrate")
async def orchestrate(orchestrator_in: OrchestratorIn):
    print("[DEBUG] /mcp/orchestrate called",orchestrator_in)
    print(f"[DEBUG] Received query: {orchestrator_in.query}")
    print(f"[DEBUG] Selected event indices: {orchestrator_in.selected_event_indices}")
    print(f"[DEBUG] Mode: {orchestrator_in.mode}")
    processed_transcripts_str = str(orchestrator_in.processed_transcripts)
    print(f"[DEBUG] Processed transcripts: {processed_transcripts_str[:100]}{'...' if len(processed_transcripts_str) > 100 else ''}")
    # Determine stage based on query (robust to natural language variants)
    q = (orchestrator_in.query or "").lower()
    stage = "fetch"
    # exact token mapping (underscore) or natural language phrases
    if q.strip() in ("process_selected_events", "process selected events", "preprocess", "preprocess selected events") or "process" in q:
        stage = "preprocess"
    elif "summarize" in q or "summary" in q:
        stage = "summarize"
    elif "jira" in q or "create jira" in q:
        stage = "jira"
    elif "risk" in q or "detect risk" in q:
        stage = "risk"
    elif "notify" in q or "notification" in q or "notify" in q:
        stage = "notify"
    print(f"[DEBUG] Determined stage: {stage}")
    print("[DEBUG] Calling orchestrator.handle_query...")
    result = orchestrator.handle_query(
        query=orchestrator_in.query,
        selected_event_indices=orchestrator_in.selected_event_indices,
        mode=orchestrator_in.mode,
        stage=stage,
        processed_transcripts=orchestrator_in.processed_transcripts,
        selected_action_items=orchestrator_in.selected_action_items
    )
    print("[DEBUG] Orchestrator result (truncated):", str(result)[:300], "..." if len(str(result)) > 100 else "result came")
    #print("[DEBUG] Orchestrator result:", result)
    
    return result
