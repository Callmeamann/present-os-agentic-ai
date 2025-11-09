from pydantic import BaseModel, Field
from typing import Literal

class ScheduleTaskPayload(BaseModel):
    task_prompt: str = Field(..., description="The task to schedule, e.g., 'go to the gym'")
    goal_id: str = Field(..., description="The ID of the goal this task is for")
    personality: Literal['P', 'A', 'E', 'I'] = Field(..., description="The PAEI personality")

class ActionRequest(BaseModel):
    task_type: Literal['schedule_task'] = Field(..., description="The type of AI action to perform")
    payload: ScheduleTaskPayload = Field(..., description="The data for this action")