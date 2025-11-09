from app.services.ai_skills.scheduling_skill import SchedulingSkill
from app.models.goal import GoalInDB
from fastapi import HTTPException 

class AIService:
    
    @staticmethod
    async def execute_task(
        task_type: str,
        user_id: str,
        payload: dict
    ) -> dict:
        """
        This is the main "LLM Engine" router.
        It routes an AI task to the correct skill.
        """
        
        if task_type == "schedule_task":
            # --- Schedule Task Skill ---
            try:
                # Extract payload for this skill
                task_prompt = payload.get("task_prompt")
                goal = payload.get("goal")
                personality = payload.get("personality")
                
                if not all([task_prompt, goal, personality]):
                    raise HTTPException(status_code=422, detail="Missing fields for schedule_task")
                
                # Call the specific skill
                event_data = await SchedulingSkill.generate_schedule_event(
                    task_prompt=task_prompt,
                    goal=goal,
                    personality=personality
                )
                return {"skill": "schedule_task", "data": event_data}

            except ValueError as e:
                raise HTTPException(status_code=500, detail=str(e))
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error in scheduling skill: {e}")
        
        # --- (Future Skill) ---
        # elif task_type == "draft_email":
        #     # 1. Extract payload
        #     # 2. Call EmailSkill.draft_email(...)
        #     # 3. return {"skill": "draft_email", "data": ...}
        
        else:
            raise HTTPException(status_code=404, detail=f"AI task_type '{task_type}' not found.")