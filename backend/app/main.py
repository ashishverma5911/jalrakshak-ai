import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .core.config import PROJECT_NAME, VERSION, API_V1_PREFIX, CORS_ORIGINS
from .api import health, sources, flood, drought, dashboard, trends, map_layers, assistant

logger = logging.getLogger("jalrakshak.api")

app = FastAPI(
    title="JalRakshak API",
    description=(
        "Flood and drought risk intelligence and preparedness decision-support prototype "
        "for Uttar Pradesh pilot locations (Gorakhpur and Mahoba)."
    ),
    version=VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers under /api/v1
app.include_router(health.router, prefix=API_V1_PREFIX)
app.include_router(sources.router, prefix=API_V1_PREFIX)
app.include_router(flood.router, prefix=API_V1_PREFIX)
app.include_router(drought.router, prefix=API_V1_PREFIX)
app.include_router(dashboard.router, prefix=API_V1_PREFIX)
app.include_router(trends.router, prefix=API_V1_PREFIX)
app.include_router(map_layers.router, prefix=API_V1_PREFIX)
app.include_router(assistant.router, prefix=API_V1_PREFIX)

@app.get("/")
def root():
    return {
        "project": "JalRakshak",
        "tagline": "Flood and Drought Risk Intelligence Prototype",
        "region": "Uttar Pradesh, India",
        "pilots": ["Gorakhpur (Flood Focus)", "Mahoba (Drought Focus)"],
        "docs": "/docs",
        "health": f"{API_V1_PREFIX}/health",
        "is_demo_data": True,
    }

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled server error on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "An unexpected server error occurred while processing environmental intelligence.",
            "path": request.url.path,
        },
    )
