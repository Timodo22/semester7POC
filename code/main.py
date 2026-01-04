from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
import os
import requests
from prometheus_client import Counter, make_asgi_app

app = FastAPI()

# CORS Setup
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus Metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# WAARSCHUWING: In productie stop je NOOIT usernames in labels (cardinality explosion).
# Voor deze POC is het echter precies wat we willen zien.
LOGIN_COUNTER = Counter(
    'login_attempts_total', 
    'Totaal aantal inlogpogingen', 
    ['status', 'ip', 'country', 'username']
)

# Database Config
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = "postgres"
DB_PASS = "postgres"
DB_NAME = "postgres"

def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS
        )
        return conn
    except Exception as e:
        print(f"Connection Error: {e}")
        # Geen raise, anders crasht de app als DB even down is
        return None

def get_country_from_ip(ip):
    try:
        # Lokale IP's negeren
        if ip == "127.0.0.1" or ip.startswith("192.168") or ip.startswith("10."):
            return "Local Network"
        
        response = requests.get(f"http://ip-api.com/json/{ip}", timeout=2)
        data = response.json()
        if data['status'] == 'success':
            return data['country']
    except:
        pass
    return "Unknown"

class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/login")
def login(request: Request, login_data: LoginRequest):
    # 1. Haal ECHTE IP adres op (ook achter proxy/loadbalancer)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        client_ip = forwarded.split(",")[0]
    else:
        client_ip = request.client.host
    
    # 2. Haal land op
    country = get_country_from_ip(client_ip)

    status = "failed"
    if login_data.password == "geheim":
        status = "success"
    
    # 3. Update Prometheus (NU MET USERNAME!)
    LOGIN_COUNTER.labels(
        status=status, 
        ip=client_ip, 
        country=country,
        username=login_data.username
    ).inc()

    # 4. Opslaan in Database
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO login_attempts (username, status) VALUES (%s, %s)", 
                (login_data.username, status)
            )
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"DB Error: {e}")

    return {"status": status, "ip": client_ip, "country": country}

@app.get("/")
def read_root():
    return {"Status": "API Online"}