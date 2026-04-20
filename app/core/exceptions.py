from __future__ import annotations

from fastapi.requests import Request
from fastapi.responses import JSONResponse


class AppException(Exception):
    pass


class ProfilesNotFoundError(AppException):
    """No profiles found"""

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


def create_exception_handler(
    initial_detail: dict, status_code: int
) -> callable[[Request, AppException], JSONResponse]:
    async def handler(request: Request, exc: AppException):
        return JSONResponse(content=initial_detail, status_code=status_code)

    return handler
