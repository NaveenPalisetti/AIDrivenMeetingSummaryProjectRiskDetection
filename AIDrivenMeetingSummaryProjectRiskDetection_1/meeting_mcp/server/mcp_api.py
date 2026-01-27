from typing import Any, Optional, List
import os

from fastapi import FastAPI, Depends, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from meeting_mcp.core.mcp import MCPHost
from meeting_mcp.tools.calendar_tool import CalendarTool
from meeting_mcp.tools.transcript_tool import TranscriptTool
from meeting_mcp.tools.summarization_tool import SummarizationTool
from meeting_mcp.agents.orchestrator_agent import OrchestratorAgent


app = FastAPI(title="meeting_mcp API")

# --- CORS setup (allow localhost during development) ---
allowed_origins = os.environ.get("MCP_ALLOWED_ORIGINS", "http://localhost,http://127.0.0.1").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def verify_api_key(x_api_key: Optional[str] = Header(None)):
    """Simple API key verification dependency. Set MCP_API_KEY env var to enable."""
    expected = os.environ.get("MCP_API_KEY")
    if expected is None:
        # No API key configured — allow local/dev usage but log a warning
        return True
    if not x_api_key or x_api_key != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API key")
    return True

# Create an in-process MCP host and register the Calendar tool
mcp_host = MCPHost()
calendar_tool = CalendarTool()
mcp_host.register_tool(calendar_tool)
transcript_tool = TranscriptTool()
mcp_host.register_tool(transcript_tool)
summarization_tool = SummarizationTool()
mcp_host.register_tool(summarization_tool)
# Register orchestrator agent wired to the same MCPHost
orchestrator = OrchestratorAgent(mcp_host=mcp_host)


class CalendarRequest(BaseModel):
    action: str
    start: Optional[Any] = None
    end: Optional[Any] = None
    calendar_id: Optional[str] = None
    event_data: Optional[dict] = None
    time_min: Optional[str] = None
    time_max: Optional[str] = None


class TranscriptRequest(BaseModel):
    transcripts: Optional[List[str]] = None
    chunk_size: Optional[int] = None
    # keep compatibility with orchestrator params
    data: Optional[Any] = None


@app.post("/mcp/calendar", dependencies=[Depends(verify_api_key)])
async def call_calendar(req: CalendarRequest):
    # create a short-lived session for this HTTP call
    session_id = mcp_host.create_session(agent_id="http-client")
    params = req.dict(exclude_none=True)
    result = await mcp_host.execute_tool(session_id, "calendar", params)
    mcp_host.end_session(session_id)
    return result


@app.post("/mcp/transcript", dependencies=[Depends(verify_api_key)])
async def call_transcript(req: TranscriptRequest):
    session_id = mcp_host.create_session(agent_id="http-client")
    params = req.dict(exclude_none=True)
    # allow `data` to alias `transcripts` for flexibility
    if "data" in params and "transcripts" not in params:
        params["transcripts"] = params.pop("data")
    result = await mcp_host.execute_tool(session_id, "transcript", params)
    mcp_host.end_session(session_id)
    return result


class OrchestrateRequest(BaseModel):
    message: str
    params: Optional[dict] = None


class SummarizeRequest(BaseModel):
    processed_transcripts: Optional[List[str]] = None
    mode: Optional[str] = None


@app.post("/mcp/orchestrate", dependencies=[Depends(verify_api_key)])
async def call_orchestrate(req: OrchestrateRequest):
    # delegate to the orchestrator agent which will create its own session and invoke tools
    result = await orchestrator.orchestrate(req.message, req.params or {})
    return result


@app.post("/mcp/summarize", dependencies=[Depends(verify_api_key)])
async def call_summarize(req: SummarizeRequest):
    session_id = mcp_host.create_session(agent_id="http-client")
    params = req.dict(exclude_none=True)
    # normalize parameter name to match tool expectations
    if "processed_transcripts" in params and "processed" not in params:
        params["processed"] = params.get("processed_transcripts")
    result = await mcp_host.execute_tool(session_id, "summarization", params)
    mcp_host.end_session(session_id)
    return result


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
