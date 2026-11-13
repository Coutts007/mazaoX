"""Framework-free domain errors. The API exception handler maps them to HTTP responses."""


class DomainError(Exception):
    def __init__(self, message: str = "", field: str = ""):
        super().__init__(message)
        self.message = message
        self.field = field


class NotFoundError(DomainError):
    pass


class ForbiddenError(DomainError):
    pass


class ConflictError(DomainError):
    pass


class InvalidInputError(DomainError):
    pass
