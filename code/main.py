from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2
import os
from prometheus_client import Counter, make_asgi_app

app = FastAPI()

# Prometheus Metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

LOGIN_COUNTER = Counter('login_attempts_total', 'Totaal aantal inlogpogingen', ['status'])

# Database Config (wordt ingevuld door Ansible via Environment Variable)
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = "postgres" # Standaard user
DB_PASS = "postgres" # Voor POC doen we even makkelijk
DB_NAME = "postgres"

def get_db_connection():
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )
    return conn

class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/login")
def login(request: LoginRequest):
    status = "failed"
    # Simpele check: wachtwoord moet 'geheim' zijn
    if request.password == "geheim":
        status = "success"
    
    # Update Prometheus Counter
    LOGIN_COUNTER.labels(status=status).inc()

    # Opslaan in Database
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO login_attempts (username, status) VALUES (%s, %s)", (request.username, status))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"DB Error: {e}")

    return {"username": request.username, "status": status, "message": "Logged in" if status == "success" else "Wrong password"}

@app.get("/")
def read_root():
    return {"Status": "API Online", "DB_Host": DB_HOST}