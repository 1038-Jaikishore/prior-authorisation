from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.connection import db_connection
from app.api.policy import router as policy_router
from app.api.policy_rag import router as policy_rag_router
from app.api.prior_auth import router as prior_auth_router
import asyncio
from contextlib import asynccontextmanager
from app.services.cms_api_service import CMSApiService

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fetch initial CMS API Token (License Agreement)
    CMSApiService.refresh_token()
    # Start the hourly background rotation worker
    asyncio.create_task(CMSApiService.token_rotation_worker())
    yield

app = FastAPI(
    title="CMS Prior Authorization Decision-Support System",
    description="A decision-support system to assist with U.S. CMS/Medicare prior-authorization workflows.",
    version="0.1.0",
    lifespan=lifespan
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

# Trigger reload for new API key
