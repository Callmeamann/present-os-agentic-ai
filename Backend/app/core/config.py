import os
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl
from typing import List, Union
from pydantic import ConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Present OS Backend"
    API_V1_STR: str = "/api/v1"
    
    # Key for encrypting/decrypting Google tokens
    SECRET_KEY: str

    # URL for our frontend, used for CORS
    FRONTEND_URL: str 

    # CORS
    # This is for any *additional* origins. We'll primarily use FRONTEND_URL
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    # Google Gemini
    GEMINI_API_KEY: str

    # Google OAuth
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str
    
    # Firebase
    FIREBASE_PROJECT_ID: str
    FIREBASE_CLIENT_EMAIL: str
    FIREBASE_PRIVATE_KEY: str
    FIREBASE_WEB_API_KEY: str

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        extra='ignore'  # Ignore extra env vars
    )

settings = Settings()