"""Domain/application errors raised by the service layer.

Routes catch these and translate to appropriate HTTP responses.
"""


class AppError(Exception):
    """Base for all application-level errors."""

    def __init__(self, message: str = ""):
        self.message = message
        super().__init__(message)


class BusinessNotFoundError(AppError):
    def __init__(self, message: str = "Business not found."):
        super().__init__(message)


class BusinessAlreadyExistsError(AppError):
    def __init__(self, message: str = "You have already added this business."):
        super().__init__(message)


class NoReviewsError(AppError):
    def __init__(self, message: str = "No reviews found for this business. Fetch reviews first."):
        super().__init__(message)


class ExternalProviderError(AppError):
    """Raised when an external service (LLM, review provider) fails."""

    def __init__(self, message: str = "External service unavailable. Please try again later."):
        super().__init__(message)


class ComparisonNotReadyError(AppError):
    """Raised when comparison prerequisites are not met."""

    def __init__(self, message: str = "Comparison prerequisites not met."):
        super().__init__(message)
