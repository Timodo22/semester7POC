from fastapi import FastAPI
import os

app = FastAPI()

@app.get("/")
def read_root():
    return {"Status": "API is online", "Deployed_By": "GitLab CI/CD"}