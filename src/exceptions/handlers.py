from fastapi import FastAPI, status
from fastapi.responses import JSONResponse

from src.exceptions.custom_exceptions import (
    BadRequestException,
    ConflictException,
    ForbiddenException,
    NotFoundException,
    UnauthorizedException,
)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFoundException)
    async def not_found_handler(_, exc: NotFoundException):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": exc.detail},
        )

    @app.exception_handler(ConflictException)
    async def conflict_handler(_, exc: ConflictException):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": exc.detail},
        )

    @app.exception_handler(BadRequestException)
    async def bad_request_handler(_, exc: BadRequestException):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": exc.detail},
        )

    @app.exception_handler(UnauthorizedException)
    async def unauthorized_handler(_, exc: UnauthorizedException):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": exc.detail},
        )

    @app.exception_handler(ForbiddenException)
    async def forbidden_handler(_, exc: ForbiddenException):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": exc.detail},
        )