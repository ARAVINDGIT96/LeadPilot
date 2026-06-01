import requests
from typing import Dict

class AIEmailGeneratorService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.1"
    
    def generate_email(self, business_name: str, business_type: str, 
                      user_name: str, user_domain: str, services: str) -> Dict:
        prompt = f"""Write a professional cold outreach email from {user_name}, a {user_domain}, to {business_name}, a {business_type} company.

The email should:
1. Friendly greeting
2. Mention discovering their business
3. Brief introduction as {user_domain}
4. Explain how you can help with: {services}
5. Call to action
6. Professional closing

Keep it 150-200 words, professional, and personalized.

Email:"""

        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": 350,
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "return_full_text": False
                }
            }
            
            response = requests.post(self.api_url, headers=headers, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    email_body = result[0].get('generated_text', '')
                    subject = f"Helping {business_name} with {user_domain} Services"
                    return {"subject": subject, "body": email_body, "status": "success"}
            
            return {"subject": "", "body": "", "status": "error", "message": "Failed to generate email"}
        
        except Exception as e:
            return {"subject": "", "body": "", "status": "error", "message": str(e)}
