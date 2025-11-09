import google.generativeai as genai
from app.core.config import settings
import json
from app.models.goal import GoalInDB

# Configure the Gemini client
genai.configure(api_key=settings.GEMINI_API_KEY)

# Use gemini-2.5-flash-preview-09-2025, it's fast, cheap, and supports JSON mode
model = genai.GenerativeModel(
    'gemini-2.5-flash-preview-09-2025',
    generation_config={"response_mime_type": "application/json"}
)

class SchedulingSkill:
    
    @staticmethod
    def _get_paei_system_prompt(personality: str, goal: GoalInDB) -> str:
        """Creates a dynamic, goal-oriented system prompt for the AI."""
        
        base_prompt = f"""
        You are an AI assistant for the 'Present OS'. Your role is to help a user schedule tasks
        that align with their high-level goals.
        
        The user's task must be framed in the context of this GOAL:
        GOAL NAME: {goal.name}
        GOAL AVATAR: {goal.avatar or 'Default'}
        GOAL DESCRIPTION: {goal.description or 'None'}

        You MUST act with a specific personality (PAEI).
        You MUST generate a JSON response with 'title', 'description', and 'duration_minutes'.
        The 'description' MUST reference the user's GOAL.
        """

        if personality.upper() == 'P':
            return base_prompt + """
            YOUR PERSONALITY IS (P)RODUCER:
            - Focus: Short-term Effectiveness.
            - Tone: Direct, action-oriented, urgent.
            - Job: Get this task done NOW. The title should be punchy.
            """
        elif personality.upper() == 'A':
            return base_prompt + """
            YOUR PERSONALITY IS (A)DMINISTRATOR:
            - Focus: Short-term Efficiency.
            - Tone: Systematic, organized, precise.
            - Job: Schedule this task logically. The title must be clear and structured.
            """
        elif personality.upper() == 'E':
            return base_prompt + """
            YOUR PERSONALITY IS (E)NTREPRENEUR:
            - Focus: Long-term Effectiveness.
            - Tone: Visionary, creative, inspiring.
            - Job: Frame this task as a step towards a bigger future. The title should be inspiring.
            """
        elif personality.upper() == 'I':
            return base_prompt + """
            YOUR PERSONALITY IS (I)NTEGRATOR:
            - Focus: Long-term Efficiency (Harmony).
            - Tone: Collaborative, empathetic, supportive.
            - Job: Frame this task as an act of self-care or connection. The title should be gentle.
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
        
        system_instruction = SchedulingSkill._get_paei_system_prompt(personality, goal)
        user_prompt = f"Task: {task_prompt}"

        try:
            response = await model.generate_content_async(
                [system_instruction, user_prompt]
            )
            
            json_text = response.text
            event_data = json.loads(json_text)
            
            if not all(k in event_data for k in ['title', 'description', 'duration_minutes']):
                raise ValueError("AI response missing required JSON keys.")
                
            return event_data

        except Exception as e:
            print(f"Error calling Gemini API for scheduling: {e}")
            # Re-raise a specific error for the service to catch
            raise ValueError(f"AI JSON generation failed: {str(e)}")