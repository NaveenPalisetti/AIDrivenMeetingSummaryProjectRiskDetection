"""
MCP Google Calendar Integration Tool

- Authenticates with Google Calendar API
- Fetches events for a given time range
- Extracts transcript text from event descriptions/notes
- Returns transcript for summarization
"""



import datetime
import os
import pickle
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from mcp.protocols.a2a import a2a_endpoint

SCOPES = ['https://www.googleapis.com/auth/calendar']

# Robust credentials path: try local, else fallback to Google Drive
cred_path_local = os.path.abspath(os.path.join(os.path.dirname(__file__), '../config/credentials.json'))
cred_path_drive = '/content/drive/MyDrive/Dissertation/Project/credentials.json'
if os.path.exists(cred_path_local):
    SERVICE_ACCOUNT_FILE = cred_path_local
elif os.path.exists(cred_path_drive):
    SERVICE_ACCOUNT_FILE = cred_path_drive
else:
    SERVICE_ACCOUNT_FILE = cred_path_local  # fallback, will error if not found


def get_oauth_credentials(scopes, cred_path='credentials.json', token_path='token.pickle'):
    """Get OAuth credentials for user consent flow."""
    creds = None
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(cred_path, scopes)
            creds = flow.run_local_server(port=0)
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)
    return creds

class MCPGoogleCalendar:
    def __init__(self, calendar_id=None):
        # Hardcode the calendar_id for now
        self.calendar_id = "naveenaitam@gmail.com"
        self.creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        self.service = build('calendar', 'v3', credentials=self.creds)

    @a2a_endpoint
    def list_attendees(self, events):
        """Return a list of attendees for each event."""
        attendees_list = []
        for event in events:
            attendees = event.get('attendees', [])
            attendee_emails = [a.get('email') for a in attendees if 'email' in a]
            attendees_list.append({
                'event_id': event.get('id'),
                'attendees': attendee_emails
            })
        return attendees_list

    @a2a_endpoint
    def create_event(self, event_data):
        """Create a new event on the calendar using the service account (no invitations sent)."""
        # Remove attendees if present, since invitations cannot be sent
        event_data.pop('attendees', None)
        event = self.service.events().insert(calendarId=self.calendar_id, body=event_data).execute()
        print(f"Created event: {event.get('id')}")
        return event

    @a2a_endpoint
    def get_availability(self, time_min, time_max):
        """Return free/busy information for the calendar between time_min and time_max (ISO format)."""
        body = {
            "timeMin": time_min,
            "timeMax": time_max,
            "items": [{"id": self.calendar_id}]
        }
        result = self.service.freebusy().query(body=body).execute()
        busy_times = result['calendars'][self.calendar_id]['busy']
        return busy_times

    @a2a_endpoint
    def summarize_events(self, events):
        """Return a simple summary (title, time, attendees count) for each event."""
        summaries = []
        for event in events:
            summary = {
                'event_id': event.get('id'),
                'title': event.get('summary', ''),
                'start': event.get('start', {}).get('dateTime', event.get('start', {}).get('date', '')),
                'end': event.get('end', {}).get('dateTime', event.get('end', {}).get('date', '')),
                'attendees_count': len(event.get('attendees', []))
            }
            summaries.append(summary)
        return summaries

    @a2a_endpoint
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

    @a2a_endpoint
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


