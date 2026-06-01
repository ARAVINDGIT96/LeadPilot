import requests
from typing import List, Dict, Optional

class BusinessDiscoveryService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://maps.googleapis.com/maps/api/place"
    
    def search_businesses(self, query: str, location: Optional[str] = None, radius: int = 5000) -> List[Dict]:
        """Search businesses using Google Places API"""
        try:
            params = {
                'query': query,
                'key': self.api_key
            }
            
            if location:
                params['location'] = location
                params['radius'] = radius
            
            response = requests.get(f"{self.base_url}/textsearch/json", params=params)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('results', [])
            return []
        except Exception as e:
            print(f"Error searching businesses: {str(e)}")
            return []
    
    def get_place_details(self, place_id: str) -> Dict:
        """Get detailed information about a place"""
        try:
            params = {
                'place_id': place_id,
                'fields': 'name,formatted_address,formatted_phone_number,website,rating,types,business_status',
                'key': self.api_key
            }
            
            response = requests.get(f"{self.base_url}/details/json", params=params)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('result', {})
            return {}
        except Exception as e:
            print(f"Error getting place details: {str(e)}")
            return {}
