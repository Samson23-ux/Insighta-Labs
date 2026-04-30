import time
import logging
from httpx import AsyncClient
from fastapi import FastAPI, Request
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.sessions import SessionMiddleware
from slowapi import _rate_limit_exceeded_handler


from app.limiter import limiter
from app.core.config import settings
from app.api.routers.auth import auth_router_v1
from app.api.routers.profiles import profile_router_v1


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.github = AsyncClient(timeout=10.0)
    app.state.agify = AsyncClient(base_url=settings.AGIFY_API_URL, timeout=10.0)
    app.state.genderize = AsyncClient(base_url=settings.GENDERIZE_API_URL, timeout=10.0)
    app.state.nationalize = AsyncClient(
        base_url=settings.NATIONALIZE_API_URL, timeout=10.0
    )

    yield

    await app.state.agify.aclose()
    await app.state.github.aclose()
    await app.state.genderize.aclose()
    await app.state.nationalize.aclose()


app = FastAPI(title=settings.API_TITLE, version=settings.API_VERSION, lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=(settings.FRONTEND_URL),
    allow_methods=("*"),
    allow_headers=("*"),
    allow_credentials=True,
)

app.add_middleware(
    SessionMiddleware,
    max_age=900,
    same_site="lax",
    secret_key=settings.SESSION_SECRET_KEY,
    https_only=settings.ENVIRONMENT == "production",
)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(auth_router_v1, prefix=settings.API_PREFIX, tags=["Auth"])
app.include_router(profile_router_v1, prefix=settings.API_PREFIX, tags=["Profiles"])


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


@app.middleware('http')
async def log_requests(request: Request, call_next):
    method, url = request.method, request.url
    start_time = time.time()

    response = await call_next(request)
    process_time = time.time() - start_time

    text = f"Method: {method}, URL: {url}, Status: {response.status_code} Time: {process_time}"
    logging.info(text)

    return response


@app.get("/", status_code=200)
async def home():
    message: dict = {
        "status": "success",
        "message": "Welcome to Profile Management and Query API!",
    }
    return message


from app.core import exception_handlers
