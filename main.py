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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
DOMAIN = os.getenv("DOMAIN", "tempemail25.chickenkiller.com")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.get("/")
def root():
    return {"status": "online"}

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "tempmail-pro"}

@app.post("/api/create")
def create_email():
    email = f"{uuid.uuid4().hex[:10]}@{DOMAIN}"
    now = datetime.utcnow()
    expires = now + timedelta(days=180)

    supabase.table("accounts").insert({
        "email": email,
        "created_at": now.isoformat(),
        "expires_at": expires.isoformat()
    }).execute()

    return {
        "email": email,
        "expires_at": expires.isoformat()
    }

@app.get("/api/accounts")
def get_accounts():
    res = supabase.table("accounts").select("*").execute()
    return res.data

@app.get("/api/inbox/{email}")
def inbox(email: str):
    res = supabase.table("messages") \
        .select("*") \
        .eq("email", email) \
        .order("created_at", desc=True) \
        .execute()

    return {
        "email": email,
        "messages": res.data
    }

@app.delete("/api/delete/{email}")
def delete_account(email: str):
    supabase.table("messages").delete().eq("email", email).execute()
    supabase.table("accounts").delete().eq("email", email).execute()

    return {"deleted": email}

@app.post("/api/inbound")
async def inbound(request: Request):
    data = await request.json()

    to_email = data.get("to")
    from_email = data.get("from")
    subject = data.get("subject")
    text = data.get("text")
    html = data.get("html")

    supabase.table("messages").insert({
        "email": to_email,
        "from_address": from_email,
        "subject": subject,
        "body": text if text else html,
        "created_at": datetime.utcnow().isoformat()
    }).execute()

    return {"status": "received"}

@app.get("/api/messages/count/{email}")
def count_messages(email: str):
    res = supabase.table("messages").select("*").eq("email", email).execute()
    return {"email": email, "count": len(res.data)}

@app.get("/api/latest/{email}")
def latest_message(email: str):
    res = supabase.table("messages") \
        .select("*") \
        .eq("email", email) \
        .order("created_at", desc=True) \
        .limit(1) \
        .execute()

    if not res.data:
        return {"message": None}

    return res.data[0]

@app.post("/api/refresh/{email}")
def refresh(email: str):
    res = supabase.table("messages") \
        .select("*") \
        .eq("email", email) \
        .order("created_at", desc=True) \
        .execute()

    return {
        "email": email,
        "messages": res.data
    }

@app.get("/api/search/{email}/{keyword}")
def search(email: str, keyword: str):
    res = supabase.table("messages") \
        .select("*") \
        .eq("email", email) \
        .execute()

    filtered = []
    for m in res.data:
        if m.get("subject") and keyword.lower() in m["subject"].lower():
            filtered.append(m)
        elif m.get("body") and keyword.lower() in str(m["body"]).lower():
            filtered.append(m)

    return {
        "email": email,
        "results": filtered
    }

@app.post("/api/cleanup")
def cleanup():
    now = datetime.utcnow().isoformat()

    expired = supabase.table("accounts") \
        .select("*") \
        .lt("expires_at", now) \
        .execute()

    for acc in expired.data:
        supabase.table("messages").delete().eq("email", acc["email"]).execute()
        supabase.table("accounts").delete().eq("email", acc["email"]).execute()

    return {"deleted_accounts": len(expired.data)}

@app.get("/api/stats")
def stats():
    accounts = supabase.table("accounts").select("*").execute()
    messages = supabase.table("messages").select("*").execute()

    return {
        "total_accounts": len(accounts.data),
        "total_messages": len(messages.data)
    }

@app.get("/api/ping")
def ping():
    return {"ping": "pong", "time": datetime.utcnow().isoformat()}

@app.post("/api/test-inbound")
def test_inbound():
    supabase.table("messages").insert({
        "email": "test@local.com",
        "from_address": "demo@test.com",
        "subject": "Test Email",
        "body": "This is a test message",
        "created_at": datetime.utcnow().isoformat()
    }).execute()

    return {"status": "inserted"}
