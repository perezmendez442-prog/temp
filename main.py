import os
import random
import string
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from supabase import create_client

# =====================
# ENV
# =====================
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
DOMAIN = os.getenv("DOMAIN", "tempemail25.chickenkiller.com")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise Exception("Falta SUPABASE_URL o SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# =====================
# APP
# =====================
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================
# DURACIONES
# =====================
DURATIONS = {
    "1h": timedelta(hours=1),
    "1d": timedelta(days=1),
    "1w": timedelta(weeks=1),
    "1m": timedelta(days=30),
    "6m": timedelta(days=180),
}

# =====================
# UTILS
# =====================
def random_username(length=10):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

# =====================
# MODELS
# =====================
class CreateAccountRequest(BaseModel):
    duration: str

class SendMessageRequest(BaseModel):
    email: str
    from_address: str
    subject: str
    body: str

# =====================
# CREATE TEMP EMAIL
# =====================
@app.post("/api/create")
def create_account(req: CreateAccountRequest):
    if req.duration not in DURATIONS:
        raise HTTPException(status_code=400, detail="Duración inválida")

    username = random_username()
    email_addr = f"{username}@{DOMAIN}"
    expires_at = (datetime.utcnow() + DURATIONS[req.duration]).isoformat()
    token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))

    supabase.table("accounts").insert({
        "email": email_addr,
        "token": token,
        "duration": req.duration,
        "expires_at": expires_at,
    }).execute()

    return {
        "email": email_addr,
        "token": token,
        "expires_at": expires_at
    }

# =====================
# SEND MESSAGE (SIMULA RECEPCIÓN REAL)
# =====================
@app.post("/api/send")
def send_message(req: SendMessageRequest):
    account = supabase.table("accounts").select("*").eq("email", req.email).execute()

    if not account.data:
        raise HTTPException(status_code=404, detail="Email no existe")

    acc = account.data[0]

    if datetime.fromisoformat(acc["expires_at"]) < datetime.utcnow():
        raise HTTPException(status_code=410, detail="Email expirado")

    supabase.table("messages").insert({
        "account_email": req.email,
        "from_address": req.from_address,
        "subject": req.subject,
        "body": req.body,
        "received_at": datetime.utcnow().isoformat()
    }).execute()

    return {"status": "mensaje guardado"}

# =====================
# GET INBOX
# =====================
@app.get("/api/messages/{token}")
def get_messages(token: str):
    account = supabase.table("accounts").select("*").eq("token", token).execute()

    if not account.data:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")

    acc = account.data[0]

    if datetime.fromisoformat(acc["expires_at"]) < datetime.utcnow():
        raise HTTPException(status_code=410, detail="Correo expirado")

    messages = supabase.table("messages") \
        .select("*") \
        .eq("account_email", acc["email"]) \
        .order("received_at", desc=True) \
        .execute()

    return {
        "email": acc["email"],
        "expires_at": acc["expires_at"],
        "messages": messages.data
    }

# =====================
# DELETE ACCOUNT
# =====================
@app.delete("/api/account/{token}")
def delete_account(token: str):
    account = supabase.table("accounts").select("*").eq("token", token).execute()

    if not account.data:
        raise HTTPException(status_code=404, detail="No existe")

    supabase.table("accounts").delete().eq("token", token).execute()

    return {"message": "eliminado"}

# =====================
# HEALTH
# =====================
@app.get("/")
def root():
    return {"status": "ok", "service": "temp mail api"}

@app.get("/api/health")
def health():
    return {"status": "running"}
