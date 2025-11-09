from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.api import api_router

# Initialize the FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# --- This is the CRITICAL CORS block ---
# We build a list of allowed origins from our .env settings
allowed_origins = [
    # This is our frontend URL: "http://localhost:3000"
    str(settings.FRONTEND_URL)
]

# This is just a helper to add any *other* origins if we defined them
if settings.BACKEND_CORS_ORIGINS:
    allowed_origins.extend([str(origin) for origin in settings.BACKEND_CORS_ORIGINS])

# Add the CORS middleware to the app
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # This tells the browser what domains are allowed
    allow_credentials=True,
    allow_methods=["*"],            # Allow all methods (GET, POST, etc.)
    allow_headers=["*"],            # Allow all headers (like "Authorization")
)
# --- End of CORS block ---

# Include our v1 API routes (from /api/v1/api.py)
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def read_root():
    """
    Root endpoint for health check.
    """
    return {"message": f"Welcome to {settings.PROJECT_NAME}"}