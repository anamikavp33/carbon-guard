import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from config import settings
import database
from routes import admin, auth, info, submissions, users
from services import ai_verification

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("carbon_guard")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate()
    try:
        database.init_db()
    except Exception as e:
        raise RuntimeError(
            f"Could not start the database ({settings.DB_MODE}): {type(e).__name__}\n"
            "Check MONGO_URI / network access in MongoDB Atlas, or run scripts/check_db.py for details."
        ) from e
    log.info("Carbon Guard backend started (DB_MODE=%s, AI: %s, satellite: %s)", settings.DB_MODE,
             ai_verification.model_status()["detail"], settings.SATELLITE_PROVIDER)
    yield
    database.close()


app = FastAPI(
    title="Carbon Guard API",
    version="3.0",
    description="Backend for Carbon Guard. The full contract with examples is in API_CONTRACT.md.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["GET", "POST", "PUT", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    # Same shape as FastAPI's default 422, but without echoing the submitted values
    # (they could contain a password).
    detail = [{"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": detail})


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    # Details go to the server log only; the client gets a safe, generic message.
    log.exception("Unexpected error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error. Please try again."})


os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
# Uploaded photos and satellite images. File names are random (uuid4), so URLs cannot be guessed.
# Prototype note: anyone who knows a URL can open it; a real deployment needs authenticated storage.
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(submissions.router)
app.include_router(admin.router)
app.include_router(info.router)


@app.get("/", tags=["health"])
def root():
    return {"message": "Carbon Guard backend is running", "docs": "/docs"}


@app.get("/health", tags=["health"])
def health():
    try:
        database.get_db().command("ping")
        db_state = "connected"
    except Exception:
        db_state = "unreachable"
    return {
        "status": "ok" if db_state == "connected" else "degraded",
        "database": db_state,
        "db_mode": settings.DB_MODE,
        "ai_model": "available" if ai_verification.model_status()["available"] else "unavailable",
        "satellite": settings.SATELLITE_PROVIDER,
        "geocoding": "enabled" if settings.GEOCODING_ENABLED else "disabled",
    }
