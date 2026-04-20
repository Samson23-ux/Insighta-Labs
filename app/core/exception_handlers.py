from fastapi import Request
from fastapi.responses import JSONResponse


from app.main import app
from app.core.exceptions import (
    QueryError,
    ServerError,
    AppException,
    ParameterError,
    InvalidTypeError,
    ProfilesNotFoundError,
    create_exception_handler
)


@app.exception_handler(ServerError)
async def server_error(request: Request, exc: AppException):
    return JSONResponse(
        content={"status": "error", "message": "Oops! Something went wrong!"},
        status_code=500,
    )


app.add_exception_handler(
    InvalidTypeError,
    create_exception_handler(
        initial_detail={
            "status": "error",
            "message": "Invalid query parameters",
        },
        status_code=422,
    ),
)


app.add_exception_handler(
    ParameterError,
    create_exception_handler(
        initial_detail={
            "status": "error",
            "message": "{param} parameter not passed",
        },
        status_code=400,
    ),
)


app.add_exception_handler(
    QueryError,
    create_exception_handler(
        initial_detail={
            "status": "error",
            "message": "Unable to interpret query",
        },
        status_code=400,
    ),
)


app.add_exception_handler(
    ProfilesNotFoundError,
    create_exception_handler(
        initial_detail={
            "status": "error",
            "message": "No profiles found at the moment! Check back later",
        },
        status_code=404,
    ),
)
