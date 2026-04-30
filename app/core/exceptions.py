from __future__ import annotations

from uuid import UUID
from fastapi.requests import Request
from fastapi.responses import JSONResponse


class AppException(Exception):
    pass


class ProfilesNotFoundError(AppException):
    """No profiles found"""

    pass


class ProfileNotFoundError(AppException):
    """No profile found for the provided name"""
    def __init__(self, profile_id: UUID):
        self.profile_id = profile_id

    pass


class QueryError(AppException):
    """user passed an unsupported query"""

    pass


class InvalidTypeError(AppException):
    """Invalid parameter type passed"""

    pass


class ParameterError(AppException):
    """Missing parameter"""

    def __init__(self, param: str):
        self.param = param


class ServerError(AppException):
    """Internal server error"""

    pass


class VersionError(AppException):
    """Version header missing"""

    pass


class MissingNameError(AppException):
    """Name parameter not passed"""

    pass


class CheckTimeoutError(AppException):
    """retry count exhausted"""

    pass


class ResponseError(AppException):
    """Invalid response received"""
    def __init__(self, external_api: str):
        self.external_api = external_api

    pass


def create_exception_handler(
    initial_detail: dict, status_code: int
) -> callable[[Request, AppException], JSONResponse]:
    async def handler(request: Request, exc: AppException):
        message: str = initial_detail.get("message")
        initial_detail["message"] = message.format(**exc.__dict__)
        return JSONResponse(content=initial_detail, status_code=status_code)

    return handler
