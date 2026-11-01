import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .core.config import PROJECT_NAME, VERSION, API_V1_PREFIX, CORS_ORIGINS, DATABASE_URL, DEMO_MODE
from .api import health, sources, flood, drought, dashboard, trends, map_layers, assistant, regions, uploads

logger = logging.getLogger("jalrakshak.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application Lifespan Management.
    In ₹0 Demo Mode or SQLite mode, ensures the spatial database schema
    and administrative region hierarchy are automatically initialized and seeded.
    """
    try:
        if DATABASE_URL.startswith("sqlite") or DEMO_MODE:
            from .db.session import engine, init_db_schema, SessionLocal
            from .db.seeds.seed_regions import seed_database
            from .db.models import Region

            init_db_schema(engine)
            with SessionLocal() as db:
                if db.query(Region).count() == 0:
                    logger.info("Initializing and seeding demo database schema...")
                    seed_database(db)
                    db.commit()
                    logger.info("Demo database seeded successfully.")
    except Exception as e:
        logger.warning(f"Startup database initialization notice: {e}")
    yield


app = FastAPI(
    title="JalRakshak API",
    description=(
        "Flood and drought risk intelligence and preparedness decision-support prototype "
        "for Uttar Pradesh pilot locations (Gorakhpur and Mahoba)."
    ),
    version=VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS configuration (safely handles wildcard domains if configured)
cors_allow_credentials = "*" not in CORS_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=cors_allow_credentials,
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
app.include_router(regions.router, prefix=API_V1_PREFIX)
app.include_router(uploads.router, prefix=API_V1_PREFIX)

@app.get("/")
def root():
    return {
        "project": "JalRakshak",
        "tagline": "Flood and Drought Risk Intelligence Prototype",
        "region": "Uttar Pradesh, India",
        "pilots": ["Gorakhpur (Flood Focus)", "Mahoba (Drought Focus)"],
        "docs": "/docs",
        "health": f"{API_V1_PREFIX}/health",
        "regions": f"{API_V1_PREFIX}/regions",
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
