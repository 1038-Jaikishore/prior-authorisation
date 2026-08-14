from fastapi import FastAPI
from app.db.connection import db_connection

app = FastAPI(
    title="CMS Prior Authorization Decision-Support System",
    description="A decision-support system to assist with U.S. CMS/Medicare prior-authorization workflows.",
    version="0.1.0"
)

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "cms-prior-auth-backend"
    }

@app.get("/health/db")
def db_health_check():
    health = db_connection.check_health()
    return health
