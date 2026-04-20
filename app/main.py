from fastapi import FastAPI


from app.core.config import settings


app = FastAPI(title=settings.API_TITLE, version=settings.API_VERSION)
