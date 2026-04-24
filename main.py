import requests
import random
import string
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MAILTM = "https://api.mail.tm"


# ---------------- UTIL ----------------
def random_pass():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=12))


# ---------------- CREATE EMAIL ----------------
class CreateReq(BaseModel):
    name: str

@app.post("/api/create")
def create(req: CreateReq):

    # obtener dominio
    domains = requests.get(f"{MAILTM}/domains").json()
    domain = domains["hydra:member"][0]["domain"]

    email = f"{req.name}{random.randint(1000,9999)}@{domain}"
    password = random_pass()

    # crear cuenta
    requests.post(f"{MAILTM}/accounts", json={
        "address": email,
        "password": password
    })

    # login
    token = requests.post(f"{MAILTM}/token", json={
        "address": email,
        "password": password
    }).json()["token"]

    return {
        "email": email,
        "password": password,
        "token": token
    }


# ---------------- GET MESSAGES ----------------
@app.get("/api/messages/{token}")
def messages(token: str):

    headers = {"Authorization": f"Bearer {token}"}

    res = requests.get(f"{MAILTM}/messages", headers=headers).json()

    return res


@app.get("/")
def home():
    return {"status": "OK - TempMail funcionando"}
