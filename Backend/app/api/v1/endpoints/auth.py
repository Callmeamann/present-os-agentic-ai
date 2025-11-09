import asyncio
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from app.services.google_service import GoogleService
from app.services.firebase_service import save_user_google_token, get_user_google_token
from app.dependencies import get_current_user
from app.core.security import TokenSecurity
from app.core.config import settings
from app.models.user import User

# This is the 'router' that api.py is looking for.
router = APIRouter()


@router.get("/google/login")
async def get_google_login(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Handles the Google login flow.
    If 'permission=true' is in the query, it checks for an existing token.
    If no token, it returns a JSON with the auth_url.
    If token exists, it returns a "permission_granted" status.
    """
    
    # This is the new logic to check for permission
    if request.query_params.get("permission") == "true":
        token = await asyncio.to_thread(get_user_google_token, current_user.uid)
        if token:
            # User already has a token, no need to redirect.
            return {"status": "permission_granted"}
        else:
            # User needs permission. Send the URL for the frontend to handle.
            try:
                auth_url = GoogleService.get_google_auth_url(state=current_user.uid)
                return {"status": "permission_needed", "auth_url": auth_url}
            except Exception as e:
                print(f"Error generating auth URL: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Could not generate Google login URL"
                )

    # This part handles the initial sign-in redirect (if we needed it)
    # But our frontend flow always uses 'permission=true',
    # so this is our main logic.
    try:
        auth_url = GoogleService.get_google_auth_url(state=current_user.uid)
        # We return JSON, not a RedirectResponse
        return {"status": "permission_needed", "auth_url": auth_url}
    except Exception as e:
        print(f"Error generating auth URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate Google login URL"
        )


@router.get("/google/callback")
async def google_auth_callback(request: Request, state: str, code: str):
    """
    Callback endpoint that Google redirects to after user consent.
    This endpoint IS allowed to send a RedirectResponse, because
    the user is on the page (not a 'fetch' request).
    """
    user_id = state 

    try:
        access_token, refresh_token = await GoogleService.get_google_tokens_from_code(code)
    except Exception as e:
        print(f"Error getting tokens from Google: {e}")
        # Redirect to the frontend with an error
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/?success=false&error=token_exchange_failed"
        )

    if not refresh_token:
        # User has already approved the app, Google doesn't send a new token.
        print(f"No refresh token returned for user {user_id}. Using existing.")
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/?success=true&message=already_authed"
        )

    try:
        encrypted_token = TokenSecurity.encrypt(refresh_token)

        await asyncio.to_thread(
            save_user_google_token,
            user_id=user_id,
            google_refresh_token=encrypted_token
        )

        # If it gets here, it worked! Redirect to frontend.
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/?success=true"
        )

    except Exception as e:
        print(f"Error during callback token processing: {e}")
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/?success=false&error=processing_failed"
        )