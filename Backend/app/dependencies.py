"""
Central place for FastAPI dependencies.
This makes it easy to manage and reuse dependencies across the API.
"""

from app.services.firebase_service import get_current_user

# By re-exporting, we can just import `get_current_user` from `app.dependencies`
# in our endpoint files. It's a small change that keeps the architecture clean.
__all__ = ["get_current_user"]