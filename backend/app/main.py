import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import health, sites, rover_photos, pathfinding, atmosphere

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ares-nav")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Tactical Martian Surface Navigator & Survival Guide - NASA Space Apps Challenge 2026",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
origins = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount modular routers under /api
app.include_router(health.router, prefix=settings.API_PREFIX)
app.include_router(sites.router, prefix=settings.API_PREFIX)
app.include_router(rover_photos.router, prefix=settings.API_PREFIX)
app.include_router(pathfinding.router, prefix=settings.API_PREFIX)
app.include_router(atmosphere.router, prefix=settings.API_PREFIX)

@app.get("/")
async def root():
    return {
        "project": settings.PROJECT_NAME,
        "challenge": "Interplanetary Survival Guide: Martian Map",
        "documentation": "/docs",
        "health": f"{settings.API_PREFIX}/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
