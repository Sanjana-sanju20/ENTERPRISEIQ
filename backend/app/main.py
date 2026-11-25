from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.auth import router as auth_router
from app.api.dashboard import router as dashboard_router
from app.api.documents import router as documents_router
from app.api.intelligence import router as intelligence_router
from app.api.workflows import router as workflows_router
from app.core.config import get_settings
from app.core.database import AsyncSessionLocal, init_db
from app.services.seed_demo import seed_demo_data

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await init_db()
    async with AsyncSessionLocal() as db:
        await seed_demo_data(db)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="EnterpriseIQ — AI-Powered Business Intelligence Management System",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exc_handler(_req: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": {"code": f"HTTP_{exc.status_code}", "message": exc.detail}})


@app.get("/api/health", tags=["System"])
async def health():
    return {"status": "ok", "service": settings.APP_NAME, "version": settings.APP_VERSION, "llm_provider": settings.LLM_PROVIDER}


app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(documents_router)
app.include_router(intelligence_router)
app.include_router(workflows_router)
