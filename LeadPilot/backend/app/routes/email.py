from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import requests
from app.auth import get_current_user
from app.database import get_supabase

router = APIRouter(prefix="/api/email", tags=["email"])

class EmailGenerationRequest(BaseModel):
    business_name: str
    business_type: str
    user_name: str
    user_domain: str
    services_offered: str
    portfolio_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    instagram_url: Optional[str] = None
    facebook_url: Optional[str] = None

@router.post("/generate")
async def generate_email(
    request: EmailGenerationRequest,
    current_user: dict = Depends(get_current_user)
):
    """Generate personalized email using Hugging Face API"""
    try:
        supabase = get_supabase()
        user_id = current_user['sub']
        
        # Get user's Hugging Face API key
        api_keys = supabase.table('api_keys').select('hugging_face_key').eq('user_id', user_id).execute()
        
        if not api_keys.data or len(api_keys.data) == 0:
            raise HTTPException(status_code=400, detail="Hugging Face API key not configured")
        
        hf_api_key = api_keys.data[0]['hugging_face_key']
        
        # Build links section
        links = []
        if request.portfolio_url:
            links.append(f"Portfolio: {request.portfolio_url}")
        if request.linkedin_url:
            links.append(f"LinkedIn: {request.linkedin_url}")
        if request.instagram_url:
            links.append(f"Instagram: {request.instagram_url}")
        if request.facebook_url:
            links.append(f"Facebook: {request.facebook_url}")
        
        links_text = "\n".join(links) if links else ""
        
        # Create email generation prompt
        prompt = f"""Write a professional business outreach email with the following details:

Business Name: {request.business_name}
Business Type: {request.business_type}
From: {request.user_name}, {request.user_domain}
Services Offered: {request.services_offered}

The email should include:
1. Professional subject line
2. Greeting to {request.business_name} team
3. Brief mention of discovering their business
4. Introduction about {request.user_name} as a {request.user_domain}
5. How {request.services_offered} can benefit their business
6. Clear call to action for a meeting or call
7. Professional closing with signature

{f"Include these links in signature: {links_text}" if links_text else ""}

Write a warm, professional, and concise email (150-200 words).
"""

        # Call Hugging Face API
        api_url = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2"
        
        headers = {
            "Authorization": f"Bearer {hf_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 500,
                "temperature": 0.7,
                "top_p": 0.95,
                "return_full_text": False
            }
        }
        
        response = requests.post(api_url, headers=headers, json=payload, timeout=30)
        
        if response.status_code != 200:
            # Fallback to template-based email if API fails
            email_body = generate_template_email(request)
            subject = f"Partnership Opportunity with {request.user_name}"
        else:
            result = response.json()
            
            if isinstance(result, list) and len(result) > 0:
                generated_text = result[0].get('generated_text', '')
                
                # Extract subject and body
                lines = generated_text.strip().split('\n')
                subject_line = None
                body_lines = []
                
                for line in lines:
                    if line.strip().lower().startswith('subject:'):
                        subject_line = line.split(':', 1)[1].strip()
                    elif line.strip():
                        body_lines.append(line)
                
                subject = subject_line if subject_line else f"Partnership Opportunity with {request.user_name}"
                email_body = '\n\n'.join(body_lines) if body_lines else generated_text
                
                # Add links if not already present
                if links_text and links_text not in email_body:
                    email_body += f"\n\n{links_text}"
            else:
                # Fallback to template
                email_body = generate_template_email(request)
                subject = f"Partnership Opportunity with {request.user_name}"
        
        return {
            "status": "success",
            "subject": subject,
            "body": email_body
        }
        
    except HTTPException:
        raise
    except requests.exceptions.Timeout:
        # Fallback to template on timeout
        email_body = generate_template_email(request)
        return {
            "status": "success",
            "subject": f"Partnership Opportunity with {request.user_name}",
            "body": email_body
        }
    except Exception as e:
        print(f"Error in generate_email: {str(e)}")
        # Fallback to template on any error
        email_body = generate_template_email(request)
        return {
            "status": "success",
            "subject": f"Partnership Opportunity with {request.user_name}",
            "body": email_body
        }

def generate_template_email(request: EmailGenerationRequest) -> str:
    """Fallback template-based email generation"""
    
    links = []
    if request.portfolio_url:
        links.append(f"Portfolio: {request.portfolio_url}")
    if request.linkedin_url:
        links.append(f"LinkedIn: {request.linkedin_url}")
    if request.instagram_url:
        links.append(f"Instagram: {request.instagram_url}")
    if request.facebook_url:
        links.append(f"Facebook: {request.facebook_url}")
    
    links_section = "\n\n" + "\n".join(links) if links else ""
    
    email = f"""Hi {request.business_name} Team,

I hope this email finds you well. I recently came across your business and was impressed by your work in the {request.business_type} industry.

My name is {request.user_name}, and I'm a {request.user_domain}. I specialize in {request.services_offered}, and I believe I can help your business achieve even greater success.

I would love to discuss how we can collaborate and explore potential opportunities that could benefit {request.business_name}. Would you be open to a quick 15-minute call next week to discuss this further?

Looking forward to hearing from you!

Best regards,
{request.user_name}
{request.user_domain}{links_section}"""
    
    return email
