"""
Tests for utility helper functions.
"""

import pytest
from datetime import datetime

from the_junior_associate.utils.helpers import (
    validate_date,
    sanitize_text,
    setup_logger,
    normalize_court_name,
    extract_case_id_from_url,
    build_search_url,
)


class TestValidateDate:
    """Tests for validate_date function."""

    def test_validate_date_with_string(self):
        """Test date validation with string input."""
        result = validate_date("2023-01-15")
        assert result == datetime(2023, 1, 15)

    def test_validate_date_with_datetime(self):
        """Test date validation with datetime input."""
        date = datetime(2023, 1, 15)
        result = validate_date(date)
        assert result == date

    def test_validate_date_with_none(self):
        """Test date validation with None input."""
        result = validate_date(None)
        assert result is None

    def test_validate_date_with_invalid_string(self):
        """Test date validation with invalid string."""
        with pytest.raises(ValueError):
            validate_date("invalid-date")


class TestSanitizeText:
    """Tests for sanitize_text function."""

    def test_sanitize_basic_text(self):
        """Test basic text sanitization."""
        result = sanitize_text("  Hello World  ")
        assert result == "Hello World"

    def test_sanitize_empty_text(self):
        """Test sanitization of empty text."""
        result = sanitize_text("")
        assert result == ""

    def test_sanitize_none_text(self):
        """Test sanitization of None."""
        result = sanitize_text(None)
        assert result == ""

    def test_sanitize_html_entities(self):
        """Test sanitization of HTML entities."""
        result = sanitize_text("Hello&nbsp;World&amp;Test")
        assert result == "Hello World&Test"

    def test_sanitize_multiple_spaces(self):
        """Test sanitization of multiple spaces."""
        result = sanitize_text("Hello    World\n\nTest")
        assert result == "Hello World Test"

    def test_sanitize_unicode_quotes(self):
        """Test sanitization of Unicode quotes."""
        text_with_smart_quotes = "\u201cHello\u201d and \u2018World\u2019"
        result = sanitize_text(text_with_smart_quotes)
        assert result == "\"Hello\" and 'World'"


class TestNormalizeCourtName:
    """Tests for normalize_court_name function."""

    def test_normalize_abbreviations(self):
        """Test normalization of court abbreviations."""
        result = normalize_court_name("S.C.")
        assert "Supreme Court" in result

    def test_normalize_empty_string(self):
        """Test normalization of empty string."""
        result = normalize_court_name("")
        assert result == ""

    def test_normalize_case_insensitive(self):
        """Test case-insensitive normalization."""
        result = normalize_court_name("h.c.")
        assert "High Court" in result


class TestExtractCaseIdFromUrl:
    """Tests for extract_case_id_from_url function."""

    def test_extract_valid_case_id(self):
        """Test extraction of valid case ID."""
        url = "https://example.com/cases/view/12345"
        pattern = r"/view/(\d+)"
        result = extract_case_id_from_url(url, pattern)
        assert result == "12345"

    def test_extract_no_match(self):
        """Test extraction with no match."""
        url = "https://example.com/cases/list"
        pattern = r"/view/(\d+)"
        result = extract_case_id_from_url(url, pattern)
        assert result is None

    def test_extract_empty_inputs(self):
        """Test extraction with empty inputs."""
        result = extract_case_id_from_url("", "")
        assert result is None


class TestBuildSearchUrl:
    """Tests for build_search_url function."""

    def test_build_url_with_params(self):
        """Test URL building with parameters."""
        base_url = "https://example.com/search"
        params = {"query": "test", "limit": 10}
        result = build_search_url(base_url, params)
        assert "query=test" in result
        assert "limit=10" in result

    def test_build_url_no_params(self):
        """Test URL building with no parameters."""
        base_url = "https://example.com/search"
        result = build_search_url(base_url, {})
        assert result == base_url

    def test_build_url_filter_none_values(self):
        """Test URL building filters None values."""
        base_url = "https://example.com/search"
        params = {"query": "test", "date": None}
        result = build_search_url(base_url, params)
        assert "query=test" in result
        assert "date" not in result


class TestSetupLogger:
    """Tests for setup_logger function."""

    def test_setup_logger_basic(self):
        """Test basic logger setup."""
        logger = setup_logger("test_logger")
        assert logger.name == "test_logger"
        assert len(logger.handlers) > 0

    def test_setup_logger_no_duplicate_handlers(self):
        """Test that duplicate handlers are not added."""
        logger1 = setup_logger("test_logger_dup")
        handler_count1 = len(logger1.handlers)

        logger2 = setup_logger("test_logger_dup")
        handler_count2 = len(logger2.handlers)

        assert handler_count1 == handler_count2
