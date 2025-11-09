import asyncio
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.services.firebase_service import (
    create_user_goal, 
    get_user_goals,
    get_user_goal # We'll add this one now for the next module
)
from app.dependencies import get_current_user
from app.models.user import User
from app.models.goal import GoalCreate, GoalInDB

# This is the 'router' that api.py is looking for.
router = APIRouter()


@router.post("/", response_model=GoalInDB, status_code=status.HTTP_201_CREATED)
async def create_new_goal(
    goal_in: GoalCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Create a new high-level goal (part of the 'RPM' framework).
    """
    try:
        # Run the synchronous database call in a separate thread
        goal_id = await asyncio.to_thread(
            create_user_goal, 
            user_id=current_user.uid, 
            goal_data=goal_in.model_dump()
        )
        
        # Return the complete object as defined by our GoalInDB model
        goal_data = goal_in.model_dump()
        goal_data['id'] = goal_id
        goal_data['user_id'] = current_user.uid
        return GoalInDB(**goal_data)
        
    except Exception as e:
        print(f"Error creating goal: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create goal."
        )


@router.get("/", response_model=List[GoalInDB])
async def get_all_user_goals(
    current_user: User = Depends(get_current_user)
):
    """
    Get all high-level goals for the authenticated user.
    """
    try:
        # Run the synchronous database call in a separate thread
        goals = await asyncio.to_thread(
            get_user_goals, 
            user_id=current_user.uid
        )
        return goals
    except Exception as e:
        print(f"Error getting goals: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve goals."
        )

@router.get("/{goal_id}", response_model=GoalInDB)
async def get_single_goal(
    goal_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get a single goal by its ID.
    """
    try:
        goal = await asyncio.to_thread(
            get_user_goal, 
            current_user.uid, 
            goal_id
        )
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found.")
        return goal
    except Exception as e:
        print(f"Error getting single goal: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve goal."
        )