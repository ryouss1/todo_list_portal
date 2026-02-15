class AppError(Exception):
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message=message, status_code=404)


class ConflictError(AppError):
    def __init__(self, message: str = "Operation conflicts with current state"):
        super().__init__(message=message, status_code=400)


class AuthenticationError(AppError):
    def __init__(self, message: str = "Not authenticated"):
        super().__init__(message=message, status_code=401)


class ForbiddenError(AppError):
    def __init__(self, message: str = "Forbidden"):
        super().__init__(message=message, status_code=403)
