from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.connection import db_connection
from app.api.policy import router as policy_router
from app.api.policy_rag import router as policy_rag_router
from app.api.prior_auth import router as prior_auth_router
from app.api.evaluation import router as evaluation_router
from app.api.decision import router as decision_router
from app.api.review import router as review_router

app = FastAPI(
    title="CMS Prior Authorization Decision-Support System",
    description="A decision-support system to assist with U.S. CMS/Medicare prior-authorization workflows.",
    version="0.1.0"
)

# Configure dev CORS
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(policy_router)
app.include_router(policy_rag_router)
app.include_router(prior_auth_router)
app.include_router(evaluation_router)
app.include_router(decision_router)
app.include_router(review_router)

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
