from fastapi import FastAPI

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
