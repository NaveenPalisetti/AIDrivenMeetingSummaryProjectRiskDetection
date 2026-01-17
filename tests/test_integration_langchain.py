from fastapi.testclient import TestClient
import os
import json
import pytest

from mcp.server.mcp_api import app
import mcp.agents.langchain_tools as lc_tools

client = TestClient(app)

@pytest.fixture(autouse=True)
def enable_lc_tools(monkeypatch):
    # Ensure tests use LangChain tools path
    monkeypatch.setenv('USE_LANGCHAIN_TOOLS', '1')
    yield


def test_orchestrate_with_mocked_lc_tools(monkeypatch):
    # Mock calendar fetch
    def mock_fetch_calendar_events_tool(user_id=None, date_range=None):
        return {"events": [{"summary":"Mock Meeting","description":"desc","created":"2026-01-01"}], "transcript": "Mock transcript text."}

    def mock_summarize_meeting(transcript: str, mode: str = "bart"):
        return {"summary": "Mock summary.", "action_items": ["Mock task 1"]}

    def mock_detect_risks_tool(summary: str = None):
        return {"risks": [{"id":"r1","description":"Mock risk","severity":"low"}]}

    def mock_send_notification_tool(task: str = None, user: str = None):
        return {"notified": True}

    monkeypatch.setattr(lc_tools, 'fetch_calendar_events_tool', mock_fetch_calendar_events_tool)
    monkeypatch.setattr(lc_tools, 'summarize_meeting', mock_summarize_meeting)
    monkeypatch.setattr(lc_tools, 'detect_risks_tool', mock_detect_risks_tool)
    monkeypatch.setattr(lc_tools, 'send_notification_tool', mock_send_notification_tool)

    payload = {"query": "fetch recent events", "mode": "bart"}
    r = client.post("/mcp/orchestrate", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert 'calendar_events' in data

    # Now call summarize
    payload = {"query": "summarize selected events", "mode": "bart", "processed_transcripts": ["A transcript."]}
    r = client.post("/mcp/orchestrate", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data.get('summaries') is not None

    # Risk
    payload = {"query": "detect risks", "mode": "bart", "summaries": ["Mock summary."]}
    r = client.post("/mcp/orchestrate", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data.get('risk') is not None

    # Notify
    payload = {"query": "notify", "mode": "bart", "summaries": ["Mock summary."], "jira": [{}], "risk": data.get('risk')}
    r = client.post("/mcp/orchestrate", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data.get('notified') is True
