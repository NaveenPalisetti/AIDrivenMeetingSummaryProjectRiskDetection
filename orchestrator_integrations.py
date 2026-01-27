"""Local integration stubs for calendar fetch, preprocessing, summarization,
risk detection, task creation and notifications.

These are intentionally light-weight placeholder implementations so the
Streamlit UI can exercise full flows without external services. Replace
with real implementations (Google API, LangChain, Twilio) when ready.
"""

from typing import List, Dict, Any
import time


def fetch_calendar_events(provider: str = 'mock', since: int = 7) -> List[Dict[str, Any]]:
    """Return a list of mock calendar events. Replace with Google/Outlook API.
    Args:
        provider: 'google'|'o365'|'mock'
        since: days back to fetch
    """
    # Simple mock: 3 events with id, summary, start, end, description
    now = int(time.time())
    events = [
        {
            'id': 'evt-001',
            'summary': 'Project Kickoff',
            'description': 'Discuss project scope and deliverables.',
            'start': {'dateTime': '2026-01-20T09:00:00+00:00'},
            'end': {'dateTime': '2026-01-20T10:00:00+00:00'},
            'attendees': [{'email': 'alice@example.com'}, {'email': 'bob@example.com'}]
        },
        {
            'id': 'evt-002',
            'summary': 'Sprint Planning',
            'description': 'Plan sprint backlog; assign stories.',
            'start': {'dateTime': '2026-01-22T11:00:00+00:00'},
            'end': {'dateTime': '2026-01-22T12:00:00+00:00'},
            'attendees': [{'email': 'carol@example.com'}]
        },
        {
            'id': 'evt-003',
            'summary': 'Retrospective',
            'description': 'What went well, what to improve.',
            'start': {'dateTime': '2026-01-25T15:00:00+00:00'},
            'end': {'dateTime': '2026-01-25T15:45:00+00:00'},
            'attendees': [{'email': 'dave@example.com'}]
        }
    ]
    return events


def preprocess_events(events: List[Dict[str, Any]]) -> List[str]:
    """Return simple processed transcripts (strings) for given events.
    Real implementation would clean, normalize, and segment transcripts.
    """
    processed = []
    for ev in events:
        text = ev.get('description', '') or ev.get('summary', '')
        # naive cleaning
        p = text.replace('\n', ' ').strip()
        processed.append(p)
    return processed


def summarize_events(processed_transcripts: List[str], model: str = 'BART') -> Dict[str, Any]:
    """Return mock summaries and action items for provided transcripts.
    Replace with actual LLM summarization chain.
    """
    summaries = []
    action_items = []
    for i, t in enumerate(processed_transcripts, start=1):
        summaries.append({'meeting_index': i, 'summary': f"Summary {i}: {t[:120]}"})
        # mock action item when 'assign' or 'assigning' appears, else one generic
        ai = {'title': f"Follow up on {i}", 'owner': None, 'due': None, 'source': f'meeting_{i}'}
        action_items.append(ai)
    return {'summaries': summaries, 'action_items': action_items}


def detect_risks(summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Return mock risk detection output. Replace with LLM-based detection.
    """
    detected = []
    for s in summaries:
        text = s.get('summary','').lower()
        if 'delay' in text or 'risk' in text:
            detected.append({'meeting_index': s.get('meeting_index'), 'risk': 'Possible delay'})
    return {'detected_risks': detected}


def create_tasks_from_action_items(action_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Create mock tasks (e.g., Jira) and return result objects."""
    tasks = []
    for i, ai in enumerate(action_items, start=1):
        tasks.append({'task_id': f'JIRA-{1000+i}', 'title': ai.get('title', f'Action {i}'), 'status': 'created'})
    return tasks


def notify_items(items: List[Dict[str, Any]], channel: str = 'inapp') -> Dict[str, Any]:
    """Mock notification sending. channel = 'inapp'|'email'|'sms'"""
    # In real usage, call Twilio / SMTP / webhook
    return {'status': 'sent', 'channel': channel, 'count': len(items)}
