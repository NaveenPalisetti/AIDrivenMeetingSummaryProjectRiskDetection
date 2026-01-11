from mcp.agents.mcp_google_calendar import MCPGoogleCalendar
import re
import datetime

class MeetingFollowupAgent:
    def __init__(self, calendar_id='primary'):
        self.calendar_id = calendar_id
        self.calendar = MCPGoogleCalendar(calendar_id=calendar_id)

    def detect_followup_intent(self, transcript: str) -> bool:
        # Simple heuristic: look for common follow-up meeting phrases
        followup_patterns = [
            r"follow[- ]?up meeting",
            r"schedule (another|a) meeting",
            r"need to (meet|discuss) again",
            r"set up (a|another) meeting",
            r"next meeting",
            r"reconvene",
            r"continue discussion"
        ]
        for pat in followup_patterns:
            if re.search(pat, transcript, re.IGNORECASE):
                return True
        return False

    def extract_meeting_details(self, transcript: str) -> dict:
        # Very basic extraction: look for date/time phrases (could be improved with NLP)
        # For now, just return None for all fields except summary
        return {
            'summary': 'Follow-up Meeting',
            'description': 'Auto-created from MCP based on transcript follow-up intent.',
            'start': None,  # Could use NLP to extract
            'end': None,    # Could use NLP to extract
            'attendees': [] # Could use NLP to extract
        }

    def create_followup_event(self, transcript: str) -> dict:
        if not self.detect_followup_intent(transcript):
            return {'created': False, 'reason': 'No follow-up intent detected.'}
        details = self.extract_meeting_details(transcript)
        # For demo: set start time to tomorrow, 1 hour duration
        now = datetime.datetime.utcnow()
        start = now + datetime.timedelta(days=1)
        end = start + datetime.timedelta(hours=1)
        event = {
            'summary': details['summary'],
            'description': details['description'],
            'start': {'dateTime': start.isoformat() + 'Z'},
            'end': {'dateTime': end.isoformat() + 'Z'},
            'attendees': details['attendees']
        }
        # Use Google Calendar API to insert event
        created_event = self.calendar.service.events().insert(calendarId=self.calendar_id, body=event).execute()
        return {'created': True, 'event': created_event}
