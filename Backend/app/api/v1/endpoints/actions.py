import asyncio
import datetime  # <-- We need this to calculate time
from fastapi import APIRouter, Depends, HTTPException, status
from app.dependencies import get_current_user
from app.models.user import User
from app.models.task import ActionRequest
from app.services.firebase_service import get_user_goal, get_user_google_token
from app.services.ai_service import AIService
from app.services.google_service import GoogleService  # <-- This is our "Arm"
from app.core.security import TokenSecurity

# This is the 'router' that api.py is looking for.
router = APIRouter()


@router.post("/", status_code=status.HTTP_201_CREATED)
async def execute_ai_action(
    request: ActionRequest,
    current_user: User = Depends(get_current_user)
):
    """
    This is the main "Action" endpoint.
    It orchestrates the entire "A++" flow.
    """
    
    # --- 1. Get User's "Purpose" (The Goal) ---
    try:
        # Get the goal from Firestore. 'goal' is a GoalInDB object.
        goal = await asyncio.to_thread(
            get_user_goal, current_user.uid, request.payload.goal_id
        )
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found. Please create the goal first.")
    except Exception as e:
        print(f"Error fetching goal: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching goal: {e}")

    # --- 2. Call the AI "Brain" (AIService) ---
    # We pass the full goal OBJECT to the AI for context
    ai_payload = {
        "task_prompt": request.payload.task_prompt,
        "goal": goal, 
        "personality": request.payload.personality
    }

    try:
        # The AI Service returns the "plan" (e.g., title, description, duration_minutes)
        ai_result = await AIService.execute_task(
            task_type=request.task_type,
            user_id=current_user.uid,
            payload=ai_payload
        )
    except HTTPException as e:
        raise e  # Re-raise HTTP exceptions from the service
    except Exception as e:
        print(f"Error in AI service: {e}")
        raise HTTPException(status_code=500, detail=f"Error in AI service: {e}")
    
    # --- 3. Execute the "Plan" (The "Arms") ---
    if request.task_type == "schedule_task":
        try:
            # 3a. Get the encrypted token
            encrypted_token = await asyncio.to_thread(get_user_google_token, current_user.uid)
            if not encrypted_token:
                raise HTTPException(status_code=401, detail="User has not authorized Google Calendar.")
            
            # 3b. Decrypt the token
            refresh_token = TokenSecurity.decrypt(encrypted_token)
            if not refresh_token:
                raise HTTPException(status_code=401, detail="Could not decrypt calendar token.")
            
            # 3c. Get event data from the AI's plan
            event_data = ai_result.get("data")
            if not event_data or 'duration_minutes' not in event_data:
                 raise HTTPException(status_code=500, detail="AI failed to return valid event data.")
            
            # --- THIS IS THE NEW LOGIC (The "Orchestration") ---
            # Calculate start/end times from the AI's duration
            duration_minutes = int(event_data.get('duration_minutes', 60))
            # Schedule the event to start 1 minute from now, in UTC
            start_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=1)
            end_time = start_time + datetime.timedelta(minutes=duration_minutes)
            # --- END OF NEW LOGIC ---

            # 3d. Create the event
            #    (This is the correct static call)
            created_event = await GoogleService.create_calendar_event(
                user_refresh_token=refresh_token,
                title=event_data.get("title"),
                description=event_data.get("description"),
                start_time=start_time, # Pass datetime object
                end_time=end_time      # Pass datetime object
            )
            
            return {
                "message": "Task scheduled successfully",
                "event_title": created_event.get("summary"),
                "event_link": created_event.get("htmlLink")
            }
        except HTTPException as e:
            raise e
        except Exception as e:
            print(f"Error creating calendar event: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to create calendar event: {str(e)}")
    
    # --- (Future task_types would be handled here) ---
    
    raise HTTPException(status_code=400, detail="Action executed but no output was produced.")