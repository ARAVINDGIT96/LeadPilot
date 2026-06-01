from pydantic import BaseModel, EmailStr, HttpUrl
from typing import Optional, List
from datetime import datetime

class UserProfile(BaseModel):
    user_id: str
    name: str
    domain: str
    portfolio_url: Optional[str] = None
    services_offered: str
    
class GmailCredentials(BaseModel):
    user_id: str
    email: EmailStr
    access_token: str
    refresh_token: str
    token_uri: str = "https://oauth2.googleapis.com/token"
    client_id: str
    client_secret: str
    
class APIKeys(BaseModel):
    user_id: str
    google_places_key: str
    hugging_face_key: str

class BusinessSearchRequest(BaseModel):
    query: str
    location: Optional[str] = None
    radius: int = 5000
    limit: int = 10

class Business(BaseModel):
    place_id: str
    name: str
    address: str
    website: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    email_confidence: int = 0
    extraction_method: Optional[str] = None
    rating: Optional[float] = None
    types: Optional[str] = None

class Campaign(BaseModel):
    campaign_id: Optional[str] = None
    user_id: str
    name: str
    status: str = "draft"  # draft, active, paused, completed
    created_at: Optional[datetime] = None
    
class CampaignBusiness(BaseModel):
    campaign_id: str
    business: Business
    email_subject: str
    email_body: str
    status: str = "pending"  # pending, sent, failed
    sent_at: Optional[datetime] = None

class EmailGenerationRequest(BaseModel):
    business_name: str
    business_type: Optional[str] = None
    business_website: Optional[str] = None
    user_name: str
    user_domain: str
    services_offered: str

class EmailSendRequest(BaseModel):
    to_email: EmailStr
    subject: str
    body: str
    campaign_id: str
    business_id: str
