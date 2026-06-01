from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import base64
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from datetime import datetime, timedelta
from app.auth import get_current_user
from app.database import get_supabase
import os
import json

# ==========================
# LOAD ENV (SAFE BACKUP)
# ==========================
from dotenv import load_dotenv
load_dotenv()

router = APIRouter(prefix="/api/gmail", tags=["gmail"])

# ==========================
# OAuth2 CONFIG (NO FALLBACKS)
# ==========================
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv(
    "GMAIL_REDIRECT_URI",
    "http://localhost:8000/api/gmail/callback"
)
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

# ==========================
# HARD FAIL IF MISCONFIGURED
# ==========================
if not CLIENT_ID:
    raise RuntimeError("❌ GOOGLE_CLIENT_ID is missing in .env")

if not CLIENT_SECRET:
    raise RuntimeError("❌ GOOGLE_CLIENT_SECRET is missing in .env")


# ==========================
# Schemas
# ==========================
class GmailAuthRequest(BaseModel):
    user_email: str


class EmailSendRequest(BaseModel):
    to: str
    subject: str
    body: str


# ==========================
# Generate OAuth URL
# ==========================
@router.get("/auth-url")
async def get_auth_url(current_user: dict = Depends(get_current_user)):
    """Generate Google OAuth2 authorization URL"""
    try:
        # 🔥 TEMPORARY DEBUG (REMOVE IN PROD)
        print("=" * 60)
        print("GMAIL OAUTH DEBUG")
        print("CLIENT_ID:", CLIENT_ID)
        print("CLIENT_SECRET:", CLIENT_SECRET[:15] + "..." if CLIENT_SECRET else None)
        print("REDIRECT_URI:", REDIRECT_URI)
        print("SCOPES:", SCOPES)
        print("=" * 60)

        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [REDIRECT_URI],
                }
            },
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI,
        )

        authorization_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )

        print("Generated Auth URL:", authorization_url[:120] + "...")
        print("STATE:", state)
        print("=" * 60)

        # Store OAuth state for CSRF protection
        supabase = get_supabase()
        user_id = current_user["sub"]

        supabase.table("gmail_oauth_states").upsert(
            {
                "user_id": user_id,
                "state": state,
                "created_at": datetime.utcnow().isoformat(),
            }
        ).execute()

        return {
            "status": "success",
            "authorization_url": authorization_url,
            "state": state,
        }

    except Exception as e:
        print("❌ Error generating auth URL:", str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ==========================
# OAuth Callback
# ==========================
@router.get("/callback")
async def oauth_callback(code: str = Query(...), state: str = Query(...)):
    """Handle OAuth2 callback from Google"""
    try:
        supabase = get_supabase()

        # Verify state
        state_result = (
            supabase.table("gmail_oauth_states")
            .select("user_id")
            .eq("state", state)
            .execute()
        )

        if not state_result.data:
            raise HTTPException(status_code=400, detail="Invalid OAuth state")

        user_id = state_result.data[0]["user_id"]

        # Exchange code for tokens
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [REDIRECT_URI],
                }
            },
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI,
        )

        flow.fetch_token(code=code)
        credentials = flow.credentials

        token_data = {
            "user_id": user_id,
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": json.dumps(credentials.scopes),
            "expiry": (datetime.utcnow() + timedelta(seconds=3600)).isoformat(),
        }

        supabase.table("gmail_tokens").upsert(token_data).execute()

        # Cleanup used state
        supabase.table("gmail_oauth_states").delete().eq("state", state).execute()

        return RedirectResponse(
            url="http://localhost:5173/dashboard?gmail=connected"
        )

    except Exception as e:
        print("❌ OAuth callback error:", str(e))
        return RedirectResponse(
            url="http://localhost:5173/dashboard?gmail=error"
        )


# ==========================
# Gmail Connection Status
# ==========================
@router.get("/status")
async def get_gmail_status(current_user: dict = Depends(get_current_user)):
    """Check if Gmail is connected"""
    try:
        supabase = get_supabase()
        user_id = current_user["sub"]

        result = (
            supabase.table("gmail_tokens")
            .select("access_token")
            .eq("user_id", user_id)
            .execute()
        )

        return {
            "status": "success",
            "connected": bool(result.data),
        }

    except Exception as e:
        print("❌ Status check error:", str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ==========================
# Disconnect Gmail
# ==========================
@router.delete("/disconnect")
async def disconnect_gmail(current_user: dict = Depends(get_current_user)):
    """Disconnect Gmail account"""
    try:
        supabase = get_supabase()
        user_id = current_user["sub"]

        supabase.table("gmail_tokens").delete().eq("user_id", user_id).execute()

        return {
            "status": "success",
            "message": "Gmail disconnected successfully",
        }

    except Exception as e:
        print("❌ Disconnect error:", str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ==========================
# Credential Helper
# ==========================
def get_gmail_credentials(user_id: str):
    """Get and refresh Gmail credentials"""
    supabase = get_supabase()

    result = (
        supabase.table("gmail_tokens")
        .select("*")
        .eq("user_id", user_id)
        .execute()
    )

    if not result.data:
        raise Exception("Gmail not connected")

    token_data = result.data[0]

    credentials = Credentials(
        token=token_data["access_token"],
        refresh_token=token_data["refresh_token"],
        token_uri=token_data["token_uri"],
        client_id=token_data["client_id"],
        client_secret=token_data["client_secret"],
        scopes=json.loads(token_data["scopes"]),
    )

    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())

        supabase.table("gmail_tokens").update(
            {
                "access_token": credentials.token,
                "expiry": (datetime.utcnow() + timedelta(seconds=3600)).isoformat(),
            }
        ).eq("user_id", user_id).execute()

    return credentials


# ==========================
# Send Email
# ==========================
@router.post("/send")
async def send_email(
    request: EmailSendRequest,
    current_user: dict = Depends(get_current_user),
):
    """Send email using Gmail API"""
    try:
        user_id = current_user["sub"]
        credentials = get_gmail_credentials(user_id)

        service = build("gmail", "v1", credentials=credentials)

        message = MIMEText(request.body)
        message["to"] = request.to
        message["subject"] = request.subject

        raw_message = base64.urlsafe_b64encode(
            message.as_bytes()
        ).decode()

        sent = (
            service.users()
            .messages()
            .send(userId="me", body={"raw": raw_message})
            .execute()
        )

        return {
            "status": "success",
            "message_id": sent["id"],
        }

    except Exception as e:
        print("❌ Send email error:", str(e))
        raise HTTPException(status_code=500, detail=str(e))
