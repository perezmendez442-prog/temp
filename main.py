from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client
from datetime import datetime, timedelta
import uuid
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔐 ENV
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
DOMAIN = os.getenv("DOMAIN", "tempemail25.chickenkiller.com")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ----------------------------
# HEALTH CHECK
# ----------------------------
@app.get("/api/health")
def health():
    return {"status": "ok"}

# ----------------------------
# CREATE TEMP EMAIL
# ----------------------------
@app.post("/api/create")
def create_email():
    email = f"{uuid.uuid4().hex[:10]}@{DOMAIN}"

    supabase.table("accounts").insert({
        "email": email,
        "expires_at": datetime.utcnow() + timedelta(days=180)
    }).execute()

    return {"email": email}

# ----------------------------
# GET INBOX
# ----------------------------
@app.get("/api/inbox/{email}")
def inbox(email: str):
    res = supabase.table("messages") \
        .select("*") \
        .eq("email", email) \
        .order("created_at", desc=True) \
        .execute()

    return res.data

# ----------------------------
# EMAIL INBOUND WEBHOOK
# ----------------------------
@app.post("/api/inbound")
async def inbound(request: Request):
    data = await request.json()

    supabase.table("messages").insert({
        "email": data.get("to"),
        "from_address": data.get("from"),
        "subject": data.get("subject"),
        "body": data.get("text") or data.get("html")
    }).execute()

    return {"ok": True}
