from pydantic import BaseModel, Field
from typing import Optional

class GoalBase(BaseModel):
    """Base Pydantic model for a Goal."""
    name: str = Field(..., description="Name of the goal (e.g., Get Healthy)")
    description: Optional[str] = Field(None, description="A short description")
    avatar: Optional[str] = Field(None, description="The 'Avatar' (e.g., Warrior, Lover)")

class GoalCreate(GoalBase):
    """Model for creating a new goal."""
    pass

class GoalInDB(GoalBase):
    """
    Model for a goal as stored in the database.
    Includes database-generated fields.
    """
    id: str = Field(..., description="The unique ID of the goal (from Firestore)")
    user_id: str = Field(..., description="The user who owns this goal")

    class Config:
        # This allows the model to be created from ORM/database objects
        from_attributes = True