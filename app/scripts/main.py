import asyncio

from app.scripts.seed_db import seed_profiles
from app.scripts.create_admin import create_admin


if __name__ == "__main__":
    asyncio.gather(create_admin(), seed_profiles())
