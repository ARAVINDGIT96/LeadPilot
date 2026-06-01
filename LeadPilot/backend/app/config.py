from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str
    
    # Auth0
    AUTH0_DOMAIN: str
    AUTH0_AUDIENCE: str
    AUTH0_API_AUDIENCE: Optional[str] = None
    AUTH0_ISSUER: Optional[str] = None
    AUTH0_ALGORITHMS: Optional[str] = "RS256"
    
    # URLs
    BACKEND_URL: Optional[str] = "http://localhost:8000"
    FRONTEND_URL: Optional[str] = "http://localhost:5173"
    ALLOWED_ORIGINS: Optional[str] = '["http://localhost:5173", "http://localhost:3000"]'
    
    # API Keys (optional, can be stored per user)
    GOOGLE_PLACES_API_KEY: Optional[str] = None
    HUGGING_FACE_API_KEY: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"  # Allow extra fields

settings = Settings()
