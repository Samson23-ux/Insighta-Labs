from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


from app.core.config import settings
from app.api.routers.profiles import profile_router


app = FastAPI(title=settings.API_TITLE, version=settings.API_VERSION)


app.add_middleware(
    CORSMiddleware,
    allow_origins=("*"),
    allow_methods=("*"),
    allow_headers=("*"),
    allow_credentials=True
)

app.include_router(profile_router, prefix=settings.API_PREFIX, tags=["Profiles"])


@app.get("/", status_code=200)
async def home():
    message: dict = {
        "status": "success",
        "message": "Welcome to Profile Management and Query API!",
    }
    return message
