import asyncio
import email
import os
import random
import string
from datetime import datetime, timedelta
from aiosmtpd.controller import Controller
from aiosmtpd.handlers import AsyncMessage
from supabase import create_client
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# ✅ VARIABLES DE ENTORNO CORRECTAS
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
DOMAIN = os.getenv("DOMAIN", "tempemail25.chickenkiller.com")

# 🔥 Validación (evita errores silenciosos)
if not SUPABASE_URL or not SUPABASE_KEY:
    raise Exception("Faltan variables de entorno SUPABASE_URL o SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DURATIONS = {
    "1h": timedelta(hours=1),
    "1d": timedelta(days=1),
    "1w": timedelta(weeks=1),
    "1m": timedelta(days=30),
    "6m": timedelta(days=180),
}

def random_username(length=10):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

# --- SMTP Handler ---
class EmailHandler(AsyncMessage):
    async def handle_message(self, message):
        try:
            to_addr = message['To']
            from_addr = message['From']
            subject = message.get('Subject', '(sin asunto)')

            if message.is_multipart():
                body = ''
                for part in message.walk():
                    if part.get_content_type() == 'text/plain':
                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        break
            else:
                body = message.get_payload(decode=True).decode('utf-8', errors='ignore')

            result = supabase.table('accounts').select('*').eq('email', to_addr).execute()
            if not result.data:
                return

            account = result.data[0]
            if datetime.fromisoformat(account['expires_at']) < datetime.now():
                return

            supabase.table('messages').insert({
                'account_email': to_addr,
                'from_address': from_addr,
                'subject': subject,
                'body': body,
            }).execute()

            print(f"Mensaje guardado: {from_addr} -> {to_addr}")
        except Exception as e:
            print(f"Error procesando email: {e}")

# --- API ---
class CreateAccountRequest(BaseModel):
    duration: str

@app.post("/api/create")
def create_account(req: CreateAccountRequest):
    if req.duration not in DURATIONS:
        raise HTTPException(status_code=400, detail="Duración inválida")

    username = random_username()
    email_addr = f"{username}@{DOMAIN}"
    expires_at = (datetime.now() + DURATIONS[req.duration]).isoformat()
    token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))

    supabase.table('accounts').insert({
        'email': email_addr,
        'token': token,
        'duration': req.duration,
        'expires_at': expires_at,
    }).execute()

    return {
        "email": email_addr,
        "token": token,
        "expires_at": expires_at,
        "duration": req.duration,
    }

@app.get("/api/messages/{token}")
def get_messages(token: str):
    account = supabase.table('accounts').select('*').eq('token', token).execute()
    if not account.data:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")

    acc = account.data[0]
    if datetime.fromisoformat(acc['expires_at']) < datetime.now():
        raise HTTPException(status_code=410, detail="Correo expirado")

    messages = supabase.table('messages').select('*').eq('account_email', acc['email']).order('received_at', desc=True).execute()

    return {
        "email": acc['email'],
        "expires_at": acc['expires_at'],
        "duration": acc['duration'],
        "messages": messages.data
    }

@app.delete("/api/account/{token}")
def delete_account(token: str):
    account = supabase.table('accounts').select('*').eq('token', token).execute()
    if not account.data:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")

    supabase.table('accounts').delete().eq('token', token).execute()
    return {"message": "Cuenta eliminada"}

@app.get("/api/health")
def health():
    return {"status": "ok"}

# --- MAIN ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))  # ✅ Render usa este puerto

    # ⚠️ SMTP desactivado en Render (puerto 25 no permitido)
    # asyncio.run(start_smtp())

    uvicorn.run(app, host="0.0.0.0", port=port)
