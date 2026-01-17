import pytest
import types
from mcp.agents.orchestrator_agent import OrchestratorAgent

class DummyCalendar:
    def __init__(self, calendar_id='primary'):
        pass
    def fetch_events(self, start_time, end_time):
        return [
            {"summary": "Team Sync", "description": "Discuss progress", "created": "2026-01-01"},
            {"summary": "Planning", "description": "Plan next sprint", "created": "2026-01-02"}
        ]
    def get_transcripts_from_events(self, events):
        return ["Transcript 1 text.", "Transcript 2 text."]

def test_fetch_stage_monkeypatch(monkeypatch):
    # Replace MCPGoogleCalendar with dummy
    import mcp.agents.orchestrator_agent as oa
    monkeypatch.setattr(oa, 'MCPGoogleCalendar', DummyCalendar)
    orchestrator = OrchestratorAgent()
    res = orchestrator.handle_query(query="fetch", stage="fetch")
    assert 'calendar_events' in res
    assert res['event_count'] == 2
    assert res['transcript_count'] == 2

def test_detect_intent_and_route():
    orchestrator = OrchestratorAgent()
    assert orchestrator._detect_intent('Please fetch my calendar events') == 'calendar'
    assert orchestrator._detect_intent('Please create a jira ticket') == 'create_jira'
    assert 'calendar_agent' in orchestrator._route_agents('calendar')
