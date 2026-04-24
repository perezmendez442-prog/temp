import os
import random
import string
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from supabase import create_client

# =========================
# ENV
# =========================
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
DOMAIN = os.getenv("DOMAIN", "tempemail25.chickenkiller.com")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise Exception("Falta SUPABASE_URL o SUPABASE_KEY en .env")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# =========================
# APP
# =========================
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# DURACIONES
# =========================
DURATIONS = {
    "1h": timedelta(hours=1),
    "1d": timedelta(days=1),
    "1w": timedelta(weeks=1),
    "1m": timedelta(days=30),
    "6m": timedelta(days=180),
}

# =========================
# UTILS
# =========================
def random_email(length=10):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

# =========================
# MODELO
# =========================
class CreateRequest(BaseModel):
    duration: str

# =========================
# ROOT
# =========================
@app.get("/")
def root():
    return {"status": "ok", "message": "TempMail API funcionando"}

# =========================
# CREAR EMAIL
# =========================
@app.post("/api/create")
def create_email(req: CreateRequest):

    if req.duration not in DURATIONS:
        raise HTTPException(status_code=400, detail="Duración inválida")

    email_name = random_email()
    email_addr = f"{email_name}@{DOMAIN}"

    expires_at = (datetime.utcnow() + DURATIONS[req.duration]).isoformat()
    token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))

    supabase.table("accounts").insert({
        "email": email_addr,
        "token": token,
        "duration": req.duration,
        "expires_at": expires_at
    }).execute()

    return {
        "email": email_addr,
        "token": token,
        "expires_at": expires_at
    }

# =========================
# VER MENSAJES
# =========================
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
        .order("created_at", desc=True) \
        .execute()

    return {
        "email": acc["email"],
        "messages": messages.data
    }

# =========================
# DELETE ACCOUNT
# =========================
@app.delete("/api/account/{token}")
def delete_account(token: str):

    account = supabase.table("accounts").select("*").eq("token", token).execute()

    if not account.data:
        raise HTTPException(status_code=404, detail="No existe")

    supabase.table("accounts").delete().eq("token", token).execute()

    return {"message": "eliminado"}
