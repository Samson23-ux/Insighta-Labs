from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_encoding="utf-8")

    API_PREFIX: str = "/api"
    API_TITLE: str = "Insighta Labs+"
    API_VERSION: str = "v1.0"

    # async db
    ASYNC_DB_URL: str

    # sync db
    SYNC_DB_URL: str

    # test db
    ASYNC_TEST_DB_URL: str

    # external api
    AGIFY_API_URL: str
    NATIONALIZE_API_URL: str
    GENDERIZE_API_URL: str

settings: Settings = Settings()
