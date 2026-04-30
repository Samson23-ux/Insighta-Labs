from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_encoding="utf-8")

    # environment
    ENVIRONMENT: str

    # api details
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
    GENDERIZE_API_URL: str
    NATIONALIZE_API_URL: str

    # JWT
    JWT_ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_TIME: int
    REFRESH_TOKEN_EXPIRE_TIME: int
    ACCESS_TOKEN_SECRET_KEY: str
    REFRESH_TOKEN_SECRET_KEY: str

    # github oauth
    GITHUB_USER_URL: str
    GITHUB_CLIENT_ID: str
    GITHUB_EMAIL_URL: str
    GITHUB_CALLBACK_URL: str
    GITHUB_CLIENT_SECRET: str
    GITHUB_AUTHORIZE_URL: str
    GITHUB_ACCESS_TOKEN_URL: str

    # session
    SESSION_SECRET_KEY: str

    # admin credentials
    ADMIN_EMAIL: str

    # cli
    GITHUB_CLI_CLIENT_ID: str
    GITHUB_CLI_CLIENT_SECRET: str
    REDIRECT_CLI_URI: str

settings: Settings = Settings()
