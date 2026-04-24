import os
import random
import string
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
DOMAIN = os.getenv("DOMAIN", "tempmail.local")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise Exception("Falta SUPABASE_URL o SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()

# CORS (OBLIGATORIO)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# FRONTEND SERVIDO DESDE FASTAPI
app.mount("/", StaticFiles(directory="static", html=True), name="static")


# =========================
# MODELOS
# =========================
class CreateRequest(BaseModel):
    duration: str


DURATIONS = {
    "1h": 1,
    "1d": 1,
    "1w": 7,
    "1m": 30,
    "6m": 180
}


# =========================
# GENERAR EMAIL
# =========================
def gen_email():
    name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    return f"{name}@{DOMAIN}"


# =========================
# CREAR CUENTA
# =========================
@app.post("/api/create")
def create(req: CreateRequest):

    if req.duration not in DURATIONS:
        raise HTTPException(status_code=400, detail="Duración inválida")

    email_addr = gen_email()
    token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))

    expires = datetime.utcnow() + timedelta(days=DURATIONS[req.duration])

    supabase.table("accounts").insert({
        "email": email_addr,
        "token": token,
        "duration": req.duration,
        "expires_at": expires.isoformat()
    }).execute()

    return {
        "email": email_addr,
        "token": token
    }


# =========================
# INBOX
# =========================
@app.get("/api/messages/{token}")
def inbox(token: str):

    acc = supabase.table("accounts").select("*").eq("token", token).execute()

    if not acc.data:
        raise HTTPException(status_code=404, detail="No existe")

    account = acc.data[0]

    msgs = supabase.table("messages") \
        .select("*") \
        .eq("account_email", account["email"]) \
        .order("received_at", desc=True) \
        .execute()

    return {
        "email": account["email"],
        "messages": msgs.data
    }



@app.get("/api/health")
def health():
    return {"status": "ok"}
