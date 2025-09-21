"""
Utilities for The Junior Associate library.
"""

from .base import BaseScraper
from .exceptions import (
    ScrapingError,
    RateLimitError,
    ParsingError,
    NetworkError,
    DataNotFoundError,
)
from .data_models import CaseData
from .helpers import validate_date, sanitize_text, setup_logger

__all__ = [
    "BaseScraper",
    "CaseData",
    "ScrapingError",
    "RateLimitError",
    "ParsingError",
    "NetworkError",
    "DataNotFoundError",
    "validate_date",
    "sanitize_text",
    "setup_logger",
]
