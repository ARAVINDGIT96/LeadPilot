from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

# ==========================
# LOAD ENV VARIABLES FIRST
# ==========================
load_dotenv()

# 🔍 TEMP DEBUG (REMOVE AFTER CONFIRMATION)
print("=" * 60)
print("ENVIRONMENT VARIABLES CHECK:")
print("SUPABASE_URL:", os.getenv("SUPABASE_URL", "NOT SET")[:40])
print("GOOGLE_CLIENT_ID:", os.getenv("GOOGLE_CLIENT_ID", "NOT SET")[:40])
print("GOOGLE_CLIENT_SECRET:", os.getenv("GOOGLE_CLIENT_SECRET", "NOT SET")[:20])
print("GMAIL_REDIRECT_URI:", os.getenv("GMAIL_REDIRECT_URI", "NOT SET"))
print("=" * 60)

# ==========================
# CREATE APP
# ==========================
app = FastAPI(
    title="LeadPilot API",
    description="AI-Powered Lead Generation & Email Outreach Platform",
    version="1.0.0"
)

# ==========================
# CORS
# ==========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================
# IMPORT ROUTES (AFTER dotenv)
# ==========================
from app.routes import user, business, campaign, gmail, email

app.include_router(user.router)
app.include_router(business.router)
app.include_router(campaign.router)
app.include_router(gmail.router)
app.include_router(email.router)

# ==========================
# HEALTH
# ==========================
@app.get("/")
async def root():
    return {
        "message": "LeadPilot API",
        "status": "operational"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
