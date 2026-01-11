"""
MCP Google Calendar Integration Tool

- Authenticates with Google Calendar API
- Fetches events for a given time range
- Extracts transcript text from event descriptions/notes
- Returns transcript for summarization
"""

import datetime
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
SERVICE_ACCOUNT_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '../config/credentials.json'))

class MCPGoogleCalendar:
    def __init__(self, calendar_id='primary'):
        self.calendar_id = calendar_id
        self.creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        self.service = build('calendar', 'v3', credentials=self.creds)

    def fetch_events(self, start_time, end_time):
        events_result = self.service.events().list(
            calendarId=self.calendar_id,
            timeMin=start_time.isoformat() + 'Z',
            timeMax=end_time.isoformat() + 'Z',
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        #print("Google Calendar API called to fetch events.",events_result)
        events = events_result.get('items', [])
        print(f"Fetched {len(events)} events from Google Calendar.")
        return events

    def get_transcripts_from_events(self, events):
        transcripts = []
        for event in events:
            desc = event.get('description', '')
            summary = event.get('summary', '')
            notes = event.get('extendedProperties', {}).get('private', {}).get('notes', '')
            transcript = '\n'.join([summary, desc, notes]).strip()
            if transcript:
                transcripts.append(transcript)
            #print(f"Event: {summary}, Transcript length: {len(transcript)} characters.")
        return transcripts

