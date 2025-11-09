import google.generativeai as genai
from app.core.config import settings
import json
from app.models.goal import GoalInDB
import datetime

genai.configure(api_key=settings.GEMINI_API_KEY)

model = genai.GenerativeModel(
    'gemini-2.5-flash-preview-09-2025',
    generation_config={"response_mime_type": "application/json"}
)

class SchedulingSkill:
    
    @staticmethod
    def _get_paei_system_prompt(
        personality: str, 
        goal: GoalInDB, 
        current_time_utc: str
    ) -> str:
        """
        Creates a dynamic, goal-oriented system prompt for the AI.
        NOW includes instructions for intelligent scheduling.
        """
        
        base_prompt = f"""
        You are an AI assistant for the 'Present OS'. Your role is to help a user schedule tasks
        that align with their high-level goals.

        ---
        USER'S GOAL CONTEXT:
        GOAL NAME: {goal.name}
        GOAL AVATAR: {goal.avatar or 'Default'}
        GOAL DESCRIPTION: {goal.description or 'None'}

        ---
        USER'S CURRENT TIME (UTC):
        {current_time_utc}

        ---
        YOUR TASK & PERSONALITY:
        You MUST act with the specific personality (PAEI) provided.
        You MUST analyze the user's task and the current time to suggest a logical schedule.
        You MUST generate a JSON response with the EXACT following keys:
        
        1. "title": (string) A title for the calendar event, matching your personality.
        2. "description": (string) A description that MUST reference the user's GOAL.
        3. "duration_minutes": (integer) An appropriate duration for this task in minutes.
        4. "start_time_iso": (string) A suggested start time in UTC ISO 8601 format (e.g., "YYYY-MM-DDTHH:MM:SSZ"). 
                                  Be intelligent: if the task is "write report", schedule it for tomorrow morning, not 2 minutes from now.
                                  If the task is "5 min meditation", 2-5 minutes from now is fine.
        5. "recurrence_rrule": (string | null) If the task seems recurring (e.g., "gym every day", "weekly review"), 
                                        provide an iCalendar RRULE string (e.g., "FREQ=DAILY;COUNT=5" or "FREQ=WEEKLY;BYDAY=MO").
                                        Follow your personality's guidance on recurrence.
                                        If it is a one-time task, you MUST return null.
        ---
        """

        if personality.upper() == 'P':
            return base_prompt + """
            YOUR PERSONALITY IS (P)RODUCER:
            - Focus: Short-term Effectiveness.
            - Tone: Direct, action-oriented, urgent.
            - Job: Get this task done NOW. The title should be punchy.
            - Scheduling: Be aggressive. Schedule it for the soonest logical time.
            - Recurrence: AVOID recurrence unless the task explicitly says "every day". Focus on THIS task.
            """
        elif personality.upper() == 'A':
            return base_prompt + """
            YOUR PERSONALITY IS (A)DMINISTRATOR:
            - Focus: Short-term Efficiency.
            - Tone: Systematic, organized, precise.
            - Job: Schedule this task logically. The title must be clear and structured.
            - Scheduling: Be systematic. Schedule it at a standard time (e.g., 9:00 AM, 2:00 PM).
            - Recurrence: If the task is a 'review', 'planning', or 'report', suggest a logical weekly recurrence (e.g., "FREQ=WEEKLY;BYDAY=MO").
            """
        elif personality.upper() == 'E':
            return base_prompt + """
            YOUR PERSONALITY IS (E)NTREPRENEUR:
            - Focus: Long-term Effectiveness.
            - Tone: Visionary, creative, inspiring.
            - Job: Frame this task as a step towards a bigger future. The title should be inspiring.
            - Scheduling: Be strategic. Give the user buffer time. Maybe schedule it for tomorrow to "prepare".
            - Recurrence: If the task builds a habit (e.g., "learn", "practice", "gym"), suggest a bold recurring schedule (e.g., "FREQ=DAILY;COUNT=7") to build momentum.
            """
        elif personality.upper() == 'I':
            return base_prompt + """
            YOUR PERSONALITY IS (I)NTEGRATOR:
            - Focus: Long-term Efficiency (Harmony).
            - Tone: Collaborative, empathetic, supportive.
            - Job: Frame this task as an act of self-care or connection. The title should be gentle.
            - Scheduling: Be flexible. Schedule it at a low-stress time, like end of day or on a weekend.
            - Recurrence: If the task is for well-being (e.g., "meditation", "walk"), suggest a gentle, flexible schedule (e.g., "FREQ=WEEKLY;BYDAY=MO,WE,FR").
            """
        else:
            return base_prompt

    @staticmethod
    async def generate_schedule_event(
        task_prompt: str,  
        goal: GoalInDB,  
        personality: str
    ) -> dict:
        """Calls the Gemini API to generate a structured calendar event."""
        
        current_time_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()

        system_instruction = SchedulingSkill._get_paei_system_prompt(
            personality, goal, current_time_utc
        )
        user_prompt = f"The user wants to schedule this task: '{task_prompt}'"

        try:
            response = await model.generate_content_async(
                [system_instruction, user_prompt]
            )
            
            json_text = response.text
            event_data = json.loads(json_text)
            
            required_keys = ['title', 'description', 'duration_minutes', 'start_time_iso']
            if not all(k in event_data for k in required_keys):
                print(f"AI response missing keys: {event_data}")
                raise ValueError("AI response missing required JSON keys.")
            
            if 'recurrence_rrule' not in event_data:
                event_data['recurrence_rrule'] = None 
                
            return event_data

        except Exception as e:
            print(f"Error calling Gemini API for scheduling: {e}")
            raise ValueError(f"AI JSON generation failed: {str(e)}")