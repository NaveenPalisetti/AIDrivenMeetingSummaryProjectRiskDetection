"""Optional real integrations for calendar, summarization, and notifications.

These functions use external libraries and require environment variables
or credential files. They are safe to import; heavy dependencies are
imported lazily inside functions and produce informative errors if
missing or not configured.

Usage: Call these from the UI when you want real integrations enabled.
If env var `USE_REAL_INTEGRATIONS` is not set, prefer the mock stubs
in `orchestrator_integrations.py`.
"""

import os
from typing import List, Dict, Any
from datetime import datetime, timedelta


def fetch_calendar_events_google(service_account_file: str = None, calendar_id: str = 'primary', days_back: int = 30) -> List[Dict[str, Any]]:
    """Fetch calendar events using a Google service account JSON file.

    Requirements: `google-api-python-client`, `google-auth`.
    Provide `GOOGLE_SERVICE_ACCOUNT_FILE` env var or pass `service_account_file`.

    Returns a list of event dicts in the same minimal shape as the mock.
    """
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except Exception as e:
        raise ImportError("Missing google client libraries. Install google-api-python-client and google-auth.") from e

    sa_file = service_account_file or os.environ.get('GOOGLE_SERVICE_ACCOUNT_FILE')
    if not sa_file or not os.path.exists(sa_file):
        raise FileNotFoundError('Google service account file not provided or not found. Set GOOGLE_SERVICE_ACCOUNT_FILE or pass path.')

    scopes = ['https://www.googleapis.com/auth/calendar.readonly']
    creds = service_account.Credentials.from_service_account_file(sa_file, scopes=scopes)
    service = build('calendar', 'v3', credentials=creds)

    time_min = (datetime.utcnow() - timedelta(days=days_back)).isoformat() + 'Z'
    events_result = service.events().list(calendarId=calendar_id, timeMin=time_min, maxResults=250, singleEvents=True, orderBy='startTime').execute()
    items = events_result.get('items', [])

    events = []
    for it in items:
        events.append({
            'id': it.get('id'),
            'summary': it.get('summary'),
            'description': it.get('description'),
            'start': it.get('start', {}),
            'end': it.get('end', {}),
            'attendees': it.get('attendees', []),
        })
    return events


def summarize_events_openai(processed_transcripts: List[str], model: str = 'gpt-4') -> Dict[str, Any]:
    """Summarize transcripts and extract action items using OpenAI Chat API.

    Requires `openai` package and `OPENAI_API_KEY` env var.
    Returns dict {summaries: [...], action_items: [...]}
    """
    try:
        import openai
    except Exception as e:
        raise ImportError('Missing openai package. Install openai to use this function.') from e

    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        raise EnvironmentError('OPENAI_API_KEY not set in environment')
    openai.api_key = api_key

    summaries = []
    action_items = []
    # A simple prompt that asks for a short summary and bullet action items
    for i, t in enumerate(processed_transcripts, start=1):
        prompt = f"You are an assistant. Given the following meeting transcript text, produce a JSON object with keys: 'summary' (1-2 sentences) and 'action_items' (list of objects with 'title','owner'(optional),'due'(optional)).\n\nTranscript:\n{t}\n\nRespond ONLY with valid JSON."
        try:
            resp = openai.ChatCompletion.create(
                model=model,
                messages=[{"role":"user","content":prompt}],
                temperature=0.2,
                max_tokens=500,
            )
            text = resp['choices'][0]['message']['content']
            # Try to parse JSON from the response
            import json as _json
            parsed = None
            try:
                parsed = _json.loads(text)
            except Exception:
                # attempt to extract JSON block
                import re
                m = re.search(r"\{.*\}", text, re.S)
                if m:
                    parsed = _json.loads(m.group(0))
            if parsed:
                summaries.append({'meeting_index': i, 'summary': parsed.get('summary')})
                ais = parsed.get('action_items', []) or []
                for ai in ais:
                    action_items.append(ai)
            else:
                summaries.append({'meeting_index': i, 'summary': text[:300]})
        except Exception as e:
            summaries.append({'meeting_index': i, 'summary': f'Error generating summary: {e}'})
    return {'summaries': summaries, 'action_items': action_items}


def notify_twilio_sms(messages: List[str], to_numbers: List[str]):
    """Send SMS messages using Twilio. Requires TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER."""
    try:
        from twilio.rest import Client
    except Exception as e:
        raise ImportError('Missing twilio package. Install twilio to use SMS notifications.') from e

    sid = os.environ.get('TWILIO_ACCOUNT_SID')
    token = os.environ.get('TWILIO_AUTH_TOKEN')
    from_num = os.environ.get('TWILIO_FROM_NUMBER')
    if not sid or not token or not from_num:
        raise EnvironmentError('Twilio credentials not set (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER)')

    client = Client(sid, token)
    results = []
    for to in to_numbers:
        for msg in messages:
            m = client.messages.create(body=msg, from_=from_num, to=to)
            results.append({'to': to, 'sid': m.sid, 'status': m.status})
    return results


def create_tasks_jira(jira_server: str, jira_user: str, jira_api_token: str, action_items: List[Dict[str, Any]]):
    """Placeholder wrapper to create Jira issues using python-jira (jira package).
    Requires JIRA credentials and server url.
    """
    try:
        from jira import JIRA
    except Exception as e:
        raise ImportError('Missing jira package. Install jira to create Jira issues.') from e

    options = {'server': jira_server}
    jira = JIRA(options, basic_auth=(jira_user, jira_api_token))
    created = []
    for ai in action_items:
        issue_dict = {
            'project': {'key': ai.get('project_key', 'PROJ')},
            'summary': ai.get('title', 'Action item'),
            'description': ai.get('description', ''),
            'issuetype': {'name': ai.get('issue_type', 'Task')},
        }
        issue = jira.create_issue(fields=issue_dict)
        created.append({'key': issue.key, 'url': f'{jira_server}/browse/{issue.key}'})
    return created
