class AppException(Exception):
    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class NotFoundException(AppException):
    pass


class ConflictException(AppException):
    pass


class BadRequestException(AppException):
    pass


class UnauthorizedException(AppException):
    pass


class ForbiddenException(AppException):
    pass