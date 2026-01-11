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
    # Determine stage based on query
    stage = "fetch"
    if orchestrator_in.query == "process_selected_events":
        stage = "preprocess"
    # Call the orchestrator agent's handle_query method
    result = orchestrator.handle_query(
        query=orchestrator_in.query,
        selected_event_indices=orchestrator_in.selected_event_indices,
        mode=orchestrator_in.mode,
        stage=stage
    )
    return result
