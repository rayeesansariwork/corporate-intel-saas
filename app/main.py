from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.v1.endpoints import router as api_router
from app.logging_config import setup_logging

# Initialize logging system
setup_logging()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="2.0.0",
    description="SaaS-Ready Corporate Intelligence Engine"
)

# CORS - Critical for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In strict prod, replace with ["https://your-frontend.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health")
def health_check():
    return {"status": "active", "version": "2.0.0"}