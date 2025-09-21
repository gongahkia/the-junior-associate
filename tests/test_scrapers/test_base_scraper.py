"""
Tests for BaseScraper functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from the_junior_associate.utils.base import BaseScraper
from the_junior_associate.utils.exceptions import (
    NetworkError,
    RateLimitError,
    ParsingError,
)


class TestBaseScraper:
    """Tests for BaseScraper class."""

    def test_base_scraper_abstract_methods(self):
        """Test that BaseScraper cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseScraper()

    def test_context_manager(self, mock_scraper_session):
        """Test context manager functionality."""

        class TestScraper(BaseScraper):
            @property
            def base_url(self):
                return "https://example.com"

            @property
            def jurisdiction(self):
                return "Test"

        with patch("requests.Session", return_value=mock_scraper_session):
            with TestScraper() as scraper:
                assert scraper.session is not None

    def test_validate_search_params(self):
        """Test search parameter validation."""

        class TestScraper(BaseScraper):
            @property
            def base_url(self):
                return "https://example.com"

            @property
            def jurisdiction(self):
                return "Test"

        scraper = TestScraper()

        # Test valid parameters
        result = scraper.validate_search_params("2023-01-01", "2023-12-31", 100)
        assert "start_date" in result
        assert "end_date" in result
        assert "limit" in result

        # Test with datetime objects
        start = datetime(2023, 1, 1)
        end = datetime(2023, 12, 31)
        result = scraper.validate_search_params(start, end, 50)
        assert result["start_date"] == start
        assert result["end_date"] == end
        assert result["limit"] == 50

    def test_validate_search_params_invalid_dates(self):
        """Test search parameter validation with invalid dates."""

        class TestScraper(BaseScraper):
            @property
            def base_url(self):
                return "https://example.com"

            @property
            def jurisdiction(self):
                return "Test"

        scraper = TestScraper()

        # Test end date before start date
        with pytest.raises(ValueError, match="End date cannot be before start date"):
            scraper.validate_search_params("2023-12-31", "2023-01-01", 100)

    def test_validate_search_params_invalid_limit(self):
        """Test search parameter validation with invalid limit."""

        class TestScraper(BaseScraper):
            @property
            def base_url(self):
                return "https://example.com"

            @property
            def jurisdiction(self):
                return "Test"

        scraper = TestScraper()

        # Test negative limit
        with pytest.raises(ValueError, match="Limit must be positive"):
            scraper.validate_search_params(None, None, -1)

        # Test zero limit
        with pytest.raises(ValueError, match="Limit must be positive"):
            scraper.validate_search_params(None, None, 0)

    @patch("requests.Session")
    def test_make_request_success(self, mock_session_class):
        """Test successful HTTP request."""

        class TestScraper(BaseScraper):
            @property
            def base_url(self):
                return "https://example.com"

            @property
            def jurisdiction(self):
                return "Test"

        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session

        scraper = TestScraper()
        response = scraper._make_request("https://example.com/test")

        assert response == mock_response
        mock_session.get.assert_called_once()

    @patch("requests.Session")
    def test_make_request_rate_limit(self, mock_session_class):
        """Test rate limiting in HTTP requests."""

        class TestScraper(BaseScraper):
            @property
            def base_url(self):
                return "https://example.com"

            @property
            def jurisdiction(self):
                return "Test"

        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "60"}
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session

        scraper = TestScraper()

        with pytest.raises(RateLimitError):
            scraper._make_request("https://example.com/test")

    @patch("requests.Session")
    def test_make_request_network_error(self, mock_session_class):
        """Test network error handling."""

        class TestScraper(BaseScraper):
            @property
            def base_url(self):
                return "https://example.com"

            @property
            def jurisdiction(self):
                return "Test"

        mock_session = Mock()
        mock_session.get.side_effect = Exception("Network error")
        mock_session_class.return_value = mock_session

        scraper = TestScraper()

        with pytest.raises(NetworkError):
            scraper._make_request("https://example.com/test")

    def test_parse_html_success(self):
        """Test HTML parsing."""

        class TestScraper(BaseScraper):
            @property
            def base_url(self):
                return "https://example.com"

            @property
            def jurisdiction(self):
                return "Test"

        scraper = TestScraper()
        html = "<html><body><h1>Test</h1></body></html>"

        soup = scraper._parse_html(html)
        assert soup.h1.text == "Test"

    def test_parse_html_invalid(self):
        """Test HTML parsing with invalid input."""

        class TestScraper(BaseScraper):
            @property
            def base_url(self):
                return "https://example.com"

            @property
            def jurisdiction(self):
                return "Test"

        scraper = TestScraper()

        with pytest.raises(ParsingError):
            scraper._parse_html(None)

    @patch("time.sleep")
    def test_wait_with_backoff(self, mock_sleep):
        """Test backoff waiting mechanism."""

        class TestScraper(BaseScraper):
            @property
            def base_url(self):
                return "https://example.com"

            @property
            def jurisdiction(self):
                return "Test"

        scraper = TestScraper()
        scraper._wait_with_backoff(1)

        mock_sleep.assert_called_once()

    def test_should_respect_rate_limit(self):
        """Test rate limit respect check."""

        class TestScraper(BaseScraper):
            @property
            def base_url(self):
                return "https://example.com"

            @property
            def jurisdiction(self):
                return "Test"

        scraper = TestScraper()

        # Initially should not need to wait
        assert not scraper._should_respect_rate_limit()

        # Set last request time to now
        scraper.last_request_time = datetime.now()

        # Should need to wait
        assert scraper._should_respect_rate_limit()

        # Set last request time to past the rate limit
        scraper.last_request_time = datetime.now() - timedelta(seconds=2)

        # Should not need to wait
        assert not scraper._should_respect_rate_limit()
