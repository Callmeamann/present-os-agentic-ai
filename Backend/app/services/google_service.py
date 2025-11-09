import httpx
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from app.core.config import settings
from typing import Dict, Any, List, Optional
import datetime
import asyncio # Import asyncio

# This is the scope we're asking for. We want to be able to
# read/write calendar events.
GOOGLE_SCOPES = ['https://www.googleapis.com/auth/calendar.events']

class GoogleService:
    """
    Handles all Google API interactions (OAuth & Calendar).
    """

    @staticmethod
    def get_google_auth_url(state: str) -> str:
        """
        Generates the Google OAuth 2.0 URL for the user to visit.
        """
        # ... existing code ...
        flow = Flow.from_client_config(
            client_config={
                "web": {
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
                }
            },
            scopes=GOOGLE_SCOPES,
            redirect_uri=settings.GOOGLE_REDIRECT_URI,
        )

        auth_url, _ = flow.authorization_url(
            access_type='offline',
            prompt='consent',
            state=state
        )
        return auth_url

    @staticmethod
    async def get_google_tokens_from_code(code: str) -> tuple[str, str] | tuple[None, None]:
        """
        Exchanges the one-time authorization `code` for an
        `access_token` and `refresh_token`.
        """
        # ... existing code ...
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
            )

        if response.status_code == 200:
        # ... existing code ...
            tokens = response.json()
            access_token = tokens.get("access_token")
            refresh_token = tokens.get("refresh_token")
            return access_token, refresh_token
        else:
            print(f"Error getting tokens: {response.text}")
            return None, None
            
    @staticmethod
    def _get_calendar_service(user_refresh_token: str):
        """
        Internal helper to build the Google Calendar service object
        from a refresh token. This is a BLOCKING call.
        """
        # ... existing code ...
        creds = Credentials(
            None,  # No access token, we will refresh
            refresh_token=user_refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            scopes=GOOGLE_SCOPES,
        )
        
        # We must refresh the credentials to get a new access token
        creds.refresh(Request())
        
        # Build the service
        service = build('calendar', 'v3', credentials=creds)
        return service

    @staticmethod
    async def create_calendar_event(
        user_refresh_token: str,
        title: str,
        description: str,
        start_time: datetime.datetime,
        end_time: datetime.datetime,
        recurrence: Optional[List[str]] = None # <-- MODIFICATION: Added argument
    ) -> Dict[str, Any]:
        """
        Creates a new event in the user's primary Google Calendar.
        Runs blocking I/O calls in a separate thread.
        """
        try:
            # Run blocking I/O in a thread to avoid blocking asyncio loop
            service = await asyncio.to_thread(
                GoogleService._get_calendar_service, user_refresh_token
            )
            
            # Convert datetimes to Google's required RFC3339 format
            start_iso = start_time.isoformat()
            end_iso = end_time.isoformat()
            
            event = {
                'summary': title,
                'description': description,
                'start': {
                    'dateTime': start_iso,
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': end_iso,
                    'timeZone': 'UTC',
                },
            }
            
            # --- MODIFICATION: Add recurrence if provided ---
            if recurrence:
                event['recurrence'] = recurrence
            # --- END MODIFICATION ---
            
            # Call the Calendar API in a thread
            created_event = await asyncio.to_thread(
                service.events().insert(
                    calendarId='primary', 
                    body=event
                ).execute
            )
            
            print(f"Event created: {created_event.get('htmlLink')}")
            return created_event

        except HttpError as error:
        # ... existing code ...
            print(f"An error occurred: {error}")
            raise Exception(f"Google Calendar API error: {error.reason}")
        except Exception as e:
            print(f"Error creating calendar event: {e}")
            raise