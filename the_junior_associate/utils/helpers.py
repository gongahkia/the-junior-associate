"""
Helper functions for The Junior Associate library.
"""

import re
import logging
from datetime import datetime
from typing import Optional, Union
from dateutil import parser as date_parser


def validate_date(date_input: Union[str, datetime, None]) -> Optional[datetime]:
    """
    Validate and convert date input to datetime object.

    Args:
        date_input: Date as string, datetime object, or None

    Returns:
        datetime object or None if invalid

    Raises:
        ValueError: If date string cannot be parsed
    """
    if date_input is None:
        return None

    if isinstance(date_input, datetime):
        return date_input

    if isinstance(date_input, str):
        try:
            return date_parser.parse(date_input)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid date format: {date_input}") from e

    raise ValueError(f"Unsupported date type: {type(date_input)}")


def sanitize_text(text: str) -> str:
    """
    Clean and sanitize text content from scraped data.

    Args:
        text: Raw text to sanitize

    Returns:
        Cleaned text
    """
    if not text:
        return ""

    # Remove extra whitespace and normalize line breaks
    text = re.sub(r'\s+', ' ', text.strip())

    # Remove HTML entities that might have been missed
    html_entities = {
        '&nbsp;': ' ',
        '&amp;': '&',
        '&lt;': '<',
        '&gt;': '>',
        '&quot;': '"',
        '&#39;': "'",
        '&apos;': "'",
    }

    for entity, replacement in html_entities.items():
        text = text.replace(entity, replacement)

    # Remove common PDF artifacts
    text = re.sub(r'\f', ' ', text)  # Form feed
    text = re.sub(r'\x0c', ' ', text)  # Form feed
    text = re.sub(r'\u00a0', ' ', text)  # Non-breaking space

    # Normalize quotes
    text = re.sub(r'["""]', '"', text)
    text = re.sub(r'[''']', "'", text)

    # Clean up multiple spaces again after replacements
    text = re.sub(r'\s+', ' ', text).strip()

    return text


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Set up a logger for the library.

    Args:
        name: Logger name
        level: Logging level

    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid duplicate handlers
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def extract_case_id_from_url(url: str, pattern: str) -> Optional[str]:
    """
    Extract case ID from URL using regex pattern.

    Args:
        url: URL to extract from
        pattern: Regex pattern to match case ID

    Returns:
        Extracted case ID or None
    """
    if not url or not pattern:
        return None

    match = re.search(pattern, url)
    return match.group(1) if match else None


def normalize_court_name(court_name: str) -> str:
    """
    Normalize court name for consistency.

    Args:
        court_name: Raw court name

    Returns:
        Normalized court name
    """
    if not court_name:
        return ""

    # Common abbreviations and normalizations
    normalizations = {
        r'\bS\.?C\.?\b': 'Supreme Court',
        r'\bC\.?A\.?\b': 'Court of Appeal',
        r'\bH\.?C\.?\b': 'High Court',
        r'\bD\.?C\.?\b': 'District Court',
        r'\bF\.?C\.?\b': 'Federal Court',
        r'\bCt\.?\b': 'Court',
        r'\bJ\.?\b': 'Justice',
    }

    result = court_name.strip()
    for pattern, replacement in normalizations.items():
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    return result.strip()


def build_search_url(base_url: str, params: dict) -> str:
    """
    Build search URL with parameters.

    Args:
        base_url: Base URL
        params: Query parameters

    Returns:
        Complete URL with parameters
    """
    if not params:
        return base_url

    # Filter out None values
    clean_params = {k: v for k, v in params.items() if v is not None}

    if not clean_params:
        return base_url

    # Build query string
    from urllib.parse import urlencode
    query_string = urlencode(clean_params)
    separator = '&' if '?' in base_url else '?'

    return f"{base_url}{separator}{query_string}"