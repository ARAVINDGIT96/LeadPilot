from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import time
from app.auth import get_current_user
from app.database import get_supabase
from app.routes.gmail import get_gmail_credentials
from googleapiclient.discovery import build
from email.mime.text import MIMEText
import base64

router = APIRouter(prefix="/api/campaign", tags=["campaign"])

class CampaignCreate(BaseModel):
    name: str
    status: str = "draft"

class CampaignBusiness(BaseModel):
    business_id: str
    business_name: str
    business_email: str
    email_subject: str
    email_body: str
    status: str = "pending"

@router.post("/")
async def create_campaign(
    campaign: CampaignCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new campaign"""
    try:
        supabase = get_supabase()
        user_id = current_user['sub']
        
        campaign_data = {
            'user_id': user_id,
            'name': campaign.name,
            'status': campaign.status,
            'total_businesses': 0,
            'emails_sent': 0,
            'emails_pending': 0
        }
        
        result = supabase.table('campaigns').insert(campaign_data).execute()
        
        return {
            "status": "success",
            "campaign": result.data[0]
        }
        
    except Exception as e:
        print(f"Error in create_campaign: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{campaign_id}/businesses")
async def add_businesses_to_campaign(
    campaign_id: str,
    businesses: List[CampaignBusiness],
    current_user: dict = Depends(get_current_user)
):
    """Add businesses to campaign"""
    try:
        supabase = get_supabase()
        user_id = current_user['sub']
        
        # Verify campaign belongs to user
        campaign = supabase.table('campaigns').select('*').eq('campaign_id', campaign_id).eq('user_id', user_id).execute()
        
        if not campaign.data:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Add businesses
        business_data = []
        for business in businesses:
            business_data.append({
                'campaign_id': campaign_id,
                'business_id': business.business_id,
                'business_name': business.business_name,
                'business_email': business.business_email,
                'email_subject': business.email_subject,
                'email_body': business.email_body,
                'status': business.status
            })
        
        result = supabase.table('campaign_businesses').insert(business_data).execute()
        
        # Update campaign counts
        total = len(businesses)
        pending = len([b for b in businesses if b.status == 'pending'])
        
        supabase.table('campaigns').update({
            'total_businesses': total,
            'emails_pending': pending
        }).eq('campaign_id', campaign_id).execute()
        
        return {
            "status": "success",
            "message": f"Added {total} businesses to campaign"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in add_businesses_to_campaign: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
async def get_campaigns(current_user: dict = Depends(get_current_user)):
    """Get all campaigns for user"""
    try:
        supabase = get_supabase()
        user_id = current_user['sub']
        
        result = supabase.table('campaigns').select('*').eq('user_id', user_id).order('created_at', desc=True).execute()
        
        return {
            "status": "success",
            "campaigns": result.data
        }
        
    except Exception as e:
        print(f"Error in get_campaigns: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{campaign_id}/businesses")
async def get_campaign_businesses(
    campaign_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all businesses in a campaign"""
    try:
        supabase = get_supabase()
        user_id = current_user['sub']
        
        # Verify campaign belongs to user
        campaign = supabase.table('campaigns').select('*').eq('campaign_id', campaign_id).eq('user_id', user_id).execute()
        
        if not campaign.data:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Get businesses
        result = supabase.table('campaign_businesses').select('*').eq('campaign_id', campaign_id).order('created_at', desc=False).execute()
        
        return {
            "status": "success",
            "businesses": result.data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_campaign_businesses: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{campaign_id}/status")
async def update_campaign_status(
    campaign_id: str,
    request: dict,  # Accept dict instead of individual parameter
    current_user: dict = Depends(get_current_user)
):
    """Update campaign status"""
    try:
        supabase = get_supabase()
        user_id = current_user['sub']
        
        # Extract status from request body
        status = request.get('status')
        
        if not status:
            raise HTTPException(status_code=400, detail="Status is required")
        
        # Validate status
        valid_statuses = ['draft', 'active', 'paused', 'completed']
        if status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
        
        result = supabase.table('campaigns').update({
            'status': status,
            'updated_at': datetime.utcnow().isoformat()
        }).eq('campaign_id', campaign_id).eq('user_id', user_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        return {
            "status": "success",
            "campaign": result.data[0]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in update_campaign_status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{campaign_id}/send")
async def send_campaign_emails(
    campaign_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Send all pending emails in campaign"""
    try:
        supabase = get_supabase()
        user_id = current_user['sub']
        
        # Verify campaign belongs to user and is active
        campaign = supabase.table('campaigns').select('*').eq('campaign_id', campaign_id).eq('user_id', user_id).execute()
        
        if not campaign.data:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        if campaign.data[0]['status'] != 'active':
            raise HTTPException(status_code=400, detail="Campaign must be active to send emails")
        
        # Get Gmail credentials
        try:
            credentials = get_gmail_credentials(user_id)
        except Exception as e:
            raise HTTPException(status_code=400, detail="Gmail not connected. Please connect your Gmail account first.")
        
        # Build Gmail service
        service = build('gmail', 'v1', credentials=credentials)
        
        # Get pending businesses
        pending_businesses = supabase.table('campaign_businesses').select('*').eq('campaign_id', campaign_id).eq('status', 'pending').execute()
        
        if not pending_businesses.data:
            return {
                "status": "success",
                "message": "No pending emails to send",
                "sent": 0,
                "failed": 0
            }
        
        sent_count = 0
        failed_count = 0
        
        # Send emails with rate limiting
        for business in pending_businesses.data:
            try:
                # Create email message
                message = MIMEText(business['email_body'])
                message['to'] = business['business_email']
                message['subject'] = business['email_subject']
                
                # Encode message
                encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
                
                # Send message
                send_result = service.users().messages().send(
                    userId='me',
                    body={'raw': encoded_message}
                ).execute()
                
                # Update business status to sent
                supabase.table('campaign_businesses').update({
                    'status': 'sent',
                    'sent_at': datetime.utcnow().isoformat()
                }).eq('id', business['id']).execute()
                
                sent_count += 1
                
                # Rate limiting: 1 second delay between emails
                time.sleep(1)
                
            except Exception as e:
                print(f"Failed to send email to {business['business_email']}: {str(e)}")
                
                # Update business status to failed
                supabase.table('campaign_businesses').update({
                    'status': 'failed',
                    'error_message': str(e)
                }).eq('id', business['id']).execute()
                
                failed_count += 1
                continue
        
        # Update campaign counts
        campaign_data = campaign.data[0]
        new_sent = campaign_data['emails_sent'] + sent_count
        new_pending = campaign_data['emails_pending'] - sent_count - failed_count
        
        supabase.table('campaigns').update({
            'emails_sent': new_sent,
            'emails_pending': max(0, new_pending)
        }).eq('campaign_id', campaign_id).execute()
        
        return {
            "status": "success",
            "message": f"Sent {sent_count} emails, {failed_count} failed",
            "sent": sent_count,
            "failed": failed_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in send_campaign_emails: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{campaign_id}/businesses/{business_id}")
async def remove_business_from_campaign(
    campaign_id: str,
    business_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Remove a business from campaign"""
    try:
        supabase = get_supabase()
        user_id = current_user['sub']
        
        # Verify campaign belongs to user
        campaign = supabase.table('campaigns').select('*').eq('campaign_id', campaign_id).eq('user_id', user_id).execute()
        
        if not campaign.data:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Get business to check status
        business = supabase.table('campaign_businesses').select('*').eq('campaign_id', campaign_id).eq('business_id', business_id).execute()
        
        if not business.data:
            raise HTTPException(status_code=404, detail="Business not found in campaign")
        
        business_status = business.data[0]['status']
        
        # Delete business
        supabase.table('campaign_businesses').delete().eq('campaign_id', campaign_id).eq('business_id', business_id).execute()
        
        # Update campaign counts
        campaign_data = campaign.data[0]
        new_total = max(0, campaign_data['total_businesses'] - 1)
        
        update_data = {'total_businesses': new_total}
        
        if business_status == 'pending':
            update_data['emails_pending'] = max(0, campaign_data['emails_pending'] - 1)
        elif business_status == 'sent':
            update_data['emails_sent'] = max(0, campaign_data['emails_sent'] - 1)
        
        supabase.table('campaigns').update(update_data).eq('campaign_id', campaign_id).execute()
        
        return {
            "status": "success",
            "message": "Business removed from campaign"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in remove_business_from_campaign: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{campaign_id}")
async def delete_campaign(
    campaign_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a campaign and all its businesses"""
    try:
        supabase = get_supabase()
        user_id = current_user['sub']
        
        # Verify campaign belongs to user
        campaign = supabase.table('campaigns').select('*').eq('campaign_id', campaign_id).eq('user_id', user_id).execute()
        
        if not campaign.data:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Delete all businesses in campaign first
        supabase.table('campaign_businesses').delete().eq('campaign_id', campaign_id).execute()
        
        # Delete campaign
        supabase.table('campaigns').delete().eq('campaign_id', campaign_id).execute()
        
        return {
            "status": "success",
            "message": "Campaign deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in delete_campaign: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
