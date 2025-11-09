import asyncio
import datetime 
from fastapi import APIRouter, Depends, HTTPException, status
from app.dependencies import get_current_user
from app.models.user import User
from app.models.task import ActionRequest
from app.services.firebase_service import get_user_goal, get_user_google_token
from app.services.ai_service import AIService
from app.services.google_service import GoogleService  
from app.core.security import TokenSecurity

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
        goal = await asyncio.to_thread(
            get_user_goal, current_user.uid, request.payload.goal_id
        )
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found. Please create the goal first.")
    except Exception as e:
        print(f"Error fetching goal: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching goal: {e}")

    # --- 2. Call the AI "Brain" (AIService) ---
    ai_payload = {
        "task_prompt": request.payload.task_prompt,
        "goal": goal, 
        "personality": request.payload.personality
    }

    try:
        ai_result = await AIService.execute_task(
            task_type=request.task_type,
            user_id=current_user.uid,
            payload=ai_payload
        )
    except HTTPException as e:
        raise e  
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
            
            # --- THIS IS THE NEW LOGIC (The "Orchestration") ---
            required_keys = ['title', 'description', 'duration_minutes', 'start_time_iso']
            if not event_data or not all(k in event_data for k in required_keys):
                 raise HTTPException(status_code=500, detail="AI failed to return valid event data.")

            # Get data from AI's plan
            duration_minutes = int(event_data['duration_minutes'])
            start_time_str = event_data['start_time_iso']
            recurrence_rrule_str = event_data.get('recurrence_rrule') 
            

            try:
                if start_time_str.endswith('Z'):
                    start_time_str = start_time_str[:-1] + '+00:00'
                start_time = datetime.datetime.fromisoformat(start_time_str)
                
                if start_time.tzinfo is None:
                     start_time = start_time.replace(tzinfo=datetime.timezone.utc)
            except ValueError as e:
                print(f"Error parsing AI-generated start time '{start_time_str}': {e}")
                start_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=1)
            
            end_time = start_time + datetime.timedelta(minutes=duration_minutes)
            
            recurrence_list = [f"RRULE:{recurrence_rrule_str}"] if recurrence_rrule_str else None

            # 3d. Create the event
            created_event = await GoogleService.create_calendar_event(
                user_refresh_token=refresh_token,
                title=event_data.get("title"),
                description=event_data.get("description"),
                start_time=start_time, 
                end_time=end_time,     
                recurrence=recurrence_list 
            )
            
            return {
                "message": "Task scheduled successfully",
                "event_title": created_event.get("summary"),
                "event_link": created_event.get("htmlLink"),
                "recurrence_applied": bool(recurrence_list)
            }
        except HTTPException as e:
            raise e
        except Exception as e:
            print(f"Error creating calendar event: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to create calendar event: {str(e)}")
    
    # --- (Future task_types would be handled here) ---
    
    raise HTTPException(status_code=400, detail="Action executed but no output was produced.")