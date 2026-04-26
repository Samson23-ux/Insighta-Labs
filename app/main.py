from fastapi import FastAPI
from httpx import AsyncClient
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware


from app.core.config import settings
from app.api.routers.profiles import profile_router_v1


app = FastAPI(title=settings.API_TITLE, version=settings.API_VERSION)


app.add_middleware(
    CORSMiddleware,
    allow_origins=("*"),
    allow_methods=("*"),
    allow_headers=("*"),
    allow_credentials=True
)

app.include_router(profile_router_v1, prefix=settings.API_PREFIX, tags=["Profiles"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.agify = AsyncClient(base_url=settings.AGIFY_API_URL, timeout=10.0)
    app.state.genderize = AsyncClient(base_url=settings.GENDERIZE_API_URL, timeout=10.0)
    app.state.nationalize = AsyncClient(base_url=settings.NATIONALIZE_API_URL, timeout=10.0)

    yield

    await app.state.agify.aclose()
    await app.state.genderize.aclose()
    await app.state.nationalize.aclose()


@app.get("/", status_code=200)
async def home():
    message: dict = {
        "status": "success",
        "message": "Welcome to Profile Management and Query API!",
    }
    return message


from app.core import exception_handlers
