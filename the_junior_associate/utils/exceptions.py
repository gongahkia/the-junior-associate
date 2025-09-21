"""
Custom exceptions for The Junior Associate library.
"""


class ScrapingError(Exception):
    """Base exception for all scraping-related errors."""

    def __init__(self, message: str, url: str = None, status_code: int = None):
        self.message = message
        self.url = url
        self.status_code = status_code
        super().__init__(self.message)

    def __str__(self):
        error_parts = [self.message]
        if self.url:
            error_parts.append(f"URL: {self.url}")
        if self.status_code:
            error_parts.append(f"Status: {self.status_code}")
        return " - ".join(error_parts)


class NetworkError(ScrapingError):
    """Raised when network-related errors occur during scraping."""
    pass


class RateLimitError(ScrapingError):
    """Raised when rate limiting is encountered."""

    def __init__(self, message: str, retry_after: int = None, url: str = None):
        self.retry_after = retry_after
        super().__init__(message, url)

    def __str__(self):
        error_str = super().__str__()
        if self.retry_after:
            error_str += f" - Retry after: {self.retry_after}s"
        return error_str


class ParsingError(ScrapingError):
    """Raised when parsing content fails."""
    pass


class AuthenticationError(ScrapingError):
    """Raised when authentication is required or fails."""
    pass


class DataNotFoundError(ScrapingError):
    """Raised when expected data cannot be found."""
    pass