import logging
import re
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import Base, engine
from routes import router

# Configure logging
logger = logging.getLogger("uvicorn.access")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Base.metadata.create_all(bind=engine) # (Usually commented out in production, use Alembic instead)
    yield

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="SafePath Backend API - Routing, Community Reports, and Journey Monitoring",
    debug=settings.APP_DEBUG,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- LOG SANITIZER MIDDLEWARE ---
@app.middleware("http")
async def sanitize_logs(request: Request, call_next):
    response = await call_next(request)
    
    # Mask any float numbers in the URL path (e.g., 17.385000 becomes 17.38***)
    # This prevents leaking exact GPS coordinates in server logs
    masked_path = re.sub(r'(\d+\.\d{2})\d+', r'\1***', str(request.url.path))
    logger.info(f"{request.method} {masked_path} - Status: {response.status_code}")
    
    return response

# Include all routes
app.include_router(router, prefix="/api/v1")

@app.get("/", tags=["Root"])
def root():
    return {
        "status": "success",
        "message": f"{settings.APP_NAME} is running",
        "docs": "/docs"
    }