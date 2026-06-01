from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import requests
from bs4 import BeautifulSoup
import re
from app.auth import get_current_user
from app.database import get_supabase

router = APIRouter(prefix="/api/business", tags=["business"])

class BusinessSearchRequest(BaseModel):
    query: str
    location: Optional[str] = None
    radius: Optional[int] = 5000
    limit: Optional[int] = 25

class Business(BaseModel):
    place_id: str
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    rating: Optional[float] = None
    types: Optional[str] = None

@router.post("/search")
async def search_businesses(
    request: BusinessSearchRequest,
    current_user: dict = Depends(get_current_user)
):
    """Search for businesses using Google Places API"""
    try:
        supabase = get_supabase()
        user_id = current_user['sub']
        
        # Get user's API key
        api_keys = supabase.table('api_keys').select('google_places_key').eq('user_id', user_id).execute()
        
        if not api_keys.data or len(api_keys.data) == 0:
            raise HTTPException(status_code=400, detail="Google Places API key not configured")
        
        google_api_key = api_keys.data[0]['google_places_key']
        
        # Google Places Text Search API
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        
        params = {
            'query': request.query,
            'key': google_api_key,
            'radius': request.radius
        }
        
        if request.location:
            params['query'] = f"{request.query} in {request.location}"
        
        response = requests.get(url, params=params)
        data = response.json()
        
        if data.get('status') != 'OK' and data.get('status') != 'ZERO_RESULTS':
            raise HTTPException(status_code=400, detail=f"Google Places API error: {data.get('status')}")
        
        businesses = []
        results = data.get('results', [])[:request.limit]
        
        for place in results:
            # Get place details for phone number
            details_url = "https://maps.googleapis.com/maps/api/place/details/json"
            details_params = {
                'place_id': place['place_id'],
                'fields': 'name,formatted_address,formatted_phone_number,website,rating,types',
                'key': google_api_key
            }
            
            details_response = requests.get(details_url, params=details_params)
            details_data = details_response.json()
            
            if details_data.get('status') == 'OK':
                result = details_data.get('result', {})
                
                business = {
                    'place_id': place['place_id'],
                    'name': result.get('name', place.get('name')),
                    'address': result.get('formatted_address', place.get('formatted_address')),
                    'phone': result.get('formatted_phone_number', 'N/A'),
                    'website': result.get('website'),
                    'rating': result.get('rating'),
                    'types': ','.join(result.get('types', []))
                }
                
                businesses.append(business)
        
        return {
            "status": "success",
            "count": len(businesses),
            "businesses": businesses
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in search_businesses: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/extract-emails")
async def extract_emails(
    businesses: List[Business],
    current_user: dict = Depends(get_current_user)
):
    """Extract email addresses from business websites"""
    try:
        def extract_email_from_website(url):
            """Scrape website to find email"""
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                response = requests.get(url, headers=headers, timeout=5)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find emails using regex
                email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                text = soup.get_text()
                emails = re.findall(email_pattern, text)
                
                # Filter out common false positives
                filtered_emails = [e for e in emails if not any(x in e.lower() for x in ['example', 'domain', 'email'])]
                
                return filtered_emails[0] if filtered_emails else None
            except:
                return None
        
        def generate_email_from_name(business_name):
            """Generate potential email from business name"""
            # Clean the name
            clean_name = re.sub(r'[^a-zA-Z0-9\s]', '', business_name.lower())
            clean_name = clean_name.replace(' ', '')
            
            # Common email patterns
            return f"contact@{clean_name}.com"
        
        updated_businesses = []
        
        for business in businesses:
            business_dict = business.dict() if hasattr(business, 'dict') else business
            
            email = None
            
            # Try to extract from website
            if business_dict.get('website'):
                email = extract_email_from_website(business_dict['website'])
            
            # If no email found, generate from business name
            if not email:
                email = generate_email_from_name(business_dict['name'])
            
            business_dict['email'] = email
            
            updated_businesses.append(business_dict)
        
        return {
            "status": "success",
            "businesses": updated_businesses
        }
        
    except Exception as e:
        print(f"Error in extract_emails: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
