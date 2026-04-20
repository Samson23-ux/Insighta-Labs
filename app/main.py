from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


from app.core.config import settings


app = FastAPI(title=settings.API_TITLE, version=settings.API_VERSION)


app.add_middleware(
    CORSMiddleware,
    allow_origins=("*"),
    allow_methods=("*"),
    allow_headers=("*"),
    allow_credentials=True
)


@app.get("/", status_code=200)
async def home():
    message: dict = {
        "status": "success",
        "message": "Welcome to Profile Management API!",
    }
    return message
