from dataclasses import dataclass


@dataclass(frozen=True)
class AppError(Exception):
    """
    Base error for domain-application specific errors.
    - code: A machine-readable error identifier for programmatic handling.
    - details: Additional context or information about the error.
    """
    code : str
    details: str = "An error occurred"

    def __str__(self) -> str:
        return f"{self.code}: {self.details}"


class NotFoundError(AppError):
    """
    Error raised when a requested resource is not found.
    """
    pass


class ConflictError(AppError):
    """
    Error raised when there is a conflict, such as duplicate entries.
    """
    pass


class UnauthorizedError(AppError):
    """
    Error raised when authentication or authorization fails.
    """
    pass


class BadRequestError(AppError):
    """
    Error raised for invalid requests or parameters.
    """
    pass


class ForbiddenError(AppError):
    """
    Error raised when access to a resource is forbidden.
    """
    pass


class ValidationError(AppError):
    """
    Error raised when data validation fails.
    """
    pass
