from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from app.database import get_supabase
from app.auth import get_current_user
import traceback

router = APIRouter(prefix="/api/user", tags=["user"])

class UserProfile(BaseModel):
    name: str
    domain: str
    portfolio_url: Optional[str] = None
    instagram_url: Optional[str] = None
    facebook_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    services_offered: str

class ApiKeys(BaseModel):
    google_places_key: str
    hugging_face_key: str

@router.post("/profile")
async def create_or_update_profile(
    profile: UserProfile,
    current_user: dict = Depends(get_current_user)
):
    """Create or update user profile"""
    try:
        supabase = get_supabase()
        user_id = current_user['sub']
        
        print(f"User ID: {user_id}")  # Debug log
        print(f"Profile data: {profile.dict()}")  # Debug log
        
        # Check if profile exists
        existing = supabase.table('user_profiles').select('*').eq('user_id', user_id).execute()
        
        profile_data = {
            'user_id': user_id,
            'name': profile.name,
            'domain': profile.domain,
            'portfolio_url': profile.portfolio_url,
            'instagram_url': profile.instagram_url,
            'facebook_url': profile.facebook_url,
            'linkedin_url': profile.linkedin_url,
            'services_offered': profile.services_offered
        }
        
        if existing.data and len(existing.data) > 0:
            # Update existing profile
            print(f"Updating existing profile for user: {user_id}")
            result = supabase.table('user_profiles').update(profile_data).eq('user_id', user_id).execute()
        else:
            # Insert new profile
            print(f"Creating new profile for user: {user_id}")
            result = supabase.table('user_profiles').insert(profile_data).execute()
        
        print(f"Result: {result.data}")  # Debug log
        
        if result.data and len(result.data) > 0:
            return {"status": "success", "profile": result.data[0]}
        else:
            raise HTTPException(status_code=500, detail="Failed to save profile")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in create_or_update_profile: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/profile")
async def get_profile(current_user: dict = Depends(get_current_user)):
    """Get user profile"""
    try:
        supabase = get_supabase()
        user_id = current_user['sub']
        
        print(f"Fetching profile for user: {user_id}")  # Debug log
        
        result = supabase.table('user_profiles').select('*').eq('user_id', user_id).execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_profile: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/api-keys")
async def save_api_keys(
    keys: ApiKeys,
    current_user: dict = Depends(get_current_user)
):
    """Save API keys"""
    try:
        supabase = get_supabase()
        user_id = current_user['sub']
        
        print(f"Saving API keys for user: {user_id}")  # Debug log
        
        # Check if exists
        existing = supabase.table('api_keys').select('*').eq('user_id', user_id).execute()
        
        keys_data = {
            'user_id': user_id,
            'google_places_key': keys.google_places_key,
            'hugging_face_key': keys.hugging_face_key
        }
        
        if existing.data and len(existing.data) > 0:
            result = supabase.table('api_keys').update(keys_data).eq('user_id', user_id).execute()
        else:
            result = supabase.table('api_keys').insert(keys_data).execute()
        
        return {"status": "success", "message": "API keys saved"}
        
    except Exception as e:
        print(f"Error in save_api_keys: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/api-keys")
async def get_api_keys(current_user: dict = Depends(get_current_user)):
    """Get API keys"""
    try:
        supabase = get_supabase()
        user_id = current_user['sub']
        
        result = supabase.table('api_keys').select('*').eq('user_id', user_id).execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=404, detail="API keys not found")
        
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_api_keys: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
