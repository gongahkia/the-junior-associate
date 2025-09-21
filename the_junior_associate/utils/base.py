"""
Base scraper class for The Junior Associate library.
"""

import time
import requests
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from bs4 import BeautifulSoup

from .exceptions import (
    ScrapingError,
    NetworkError,
    RateLimitError,
    ParsingError,
    AuthenticationError,
)
from .data_models import CaseData
from .helpers import setup_logger, validate_date, sanitize_text


class BaseScraper(ABC):
    """
    Base class for all legal case scrapers.

    Provides common functionality including:
    - HTTP session management
    - Rate limiting
    - Error handling
    - Retry logic
    - Logging
    """

    def __init__(
        self,
        rate_limit: float = 1.0,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        user_agent: str = None,
    ):
        """
        Initialize the base scraper.

        Args:
            rate_limit: Minimum seconds between requests
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_delay: Base delay between retries in seconds
            user_agent: Custom user agent string
        """
        self.rate_limit = rate_limit
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._last_request_time = 0.0

        # Set up session
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": user_agent or self._default_user_agent(),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
        )

        # Set up logging
        self.logger = setup_logger(f"{self.__class__.__name__}")

    @property
    @abstractmethod
    def base_url(self) -> str:
        """Base URL for the legal database."""
        pass

    @property
    @abstractmethod
    def jurisdiction(self) -> str:
        """Jurisdiction covered by this scraper."""
        pass

    def _default_user_agent(self) -> str:
        """Default user agent string."""
        return (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )

    def _respect_rate_limit(self):
        """Enforce rate limiting between requests."""
        if self.rate_limit > 0:
            elapsed = time.time() - self._last_request_time
            if elapsed < self.rate_limit:
                sleep_time = self.rate_limit - elapsed
                self.logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
                time.sleep(sleep_time)

    def _make_request(
        self,
        url: str,
        method: str = "GET",
        params: Dict[str, Any] = None,
        data: Dict[str, Any] = None,
        headers: Dict[str, str] = None,
    ) -> requests.Response:
        """
        Make HTTP request with retry logic and error handling.

        Args:
            url: URL to request
            method: HTTP method
            params: Query parameters
            data: POST data
            headers: Additional headers

        Returns:
            Response object

        Raises:
            NetworkError: For network-related issues
            RateLimitError: When rate limited
            AuthenticationError: For auth issues
        """
        self._respect_rate_limit()

        # Merge headers
        request_headers = self.session.headers.copy()
        if headers:
            request_headers.update(headers)

        for attempt in range(self.max_retries + 1):
            try:
                self.logger.debug(
                    f"Making {method} request to {url} (attempt {attempt + 1})"
                )

                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    data=data,
                    headers=request_headers,
                    timeout=self.timeout,
                )

                self._last_request_time = time.time()

                # Handle HTTP status codes
                if response.status_code == 200:
                    return response
                elif response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    raise RateLimitError(
                        f"Rate limited (429)", retry_after=retry_after, url=url
                    )
                elif response.status_code in (401, 403):
                    raise AuthenticationError(
                        f"Authentication required ({response.status_code})",
                        url=url,
                        status_code=response.status_code,
                    )
                elif response.status_code >= 500:
                    if attempt < self.max_retries:
                        self.logger.warning(
                            f"Server error {response.status_code}, retrying in "
                            f"{self.retry_delay}s"
                        )
                        time.sleep(self.retry_delay * (2**attempt))
                        continue
                    else:
                        raise NetworkError(
                            f"Server error ({response.status_code})",
                            url=url,
                            status_code=response.status_code,
                        )
                else:
                    raise NetworkError(
                        f"HTTP {response.status_code}",
                        url=url,
                        status_code=response.status_code,
                    )

            except requests.exceptions.Timeout:
                if attempt < self.max_retries:
                    self.logger.warning(
                        f"Request timeout, retrying in {self.retry_delay}s"
                    )
                    time.sleep(self.retry_delay * (2**attempt))
                    continue
                else:
                    raise NetworkError(
                        f"Request timeout after {self.max_retries} retries", url=url
                    )

            except requests.exceptions.ConnectionError as e:
                if attempt < self.max_retries:
                    self.logger.warning(
                        f"Connection error, retrying in {self.retry_delay}s"
                    )
                    time.sleep(self.retry_delay * (2**attempt))
                    continue
                else:
                    raise NetworkError(f"Connection failed: {str(e)}", url=url)

            except requests.exceptions.RequestException as e:
                raise NetworkError(f"Request failed: {str(e)}", url=url)

        # Should not reach here
        raise NetworkError(f"Failed after {self.max_retries} retries", url=url)

    def _parse_html(self, content: str) -> BeautifulSoup:
        """
        Parse HTML content using BeautifulSoup.

        Args:
            content: HTML content to parse

        Returns:
            BeautifulSoup object

        Raises:
            ParsingError: If parsing fails
        """
        try:
            return BeautifulSoup(content, "lxml")
        except Exception as e:
            try:
                return BeautifulSoup(content, "html.parser")
            except Exception as e2:
                raise ParsingError(f"Failed to parse HTML: {str(e2)}") from e2

    @abstractmethod
    def search_cases(
        self,
        query: str = None,
        start_date: Union[str, datetime] = None,
        end_date: Union[str, datetime] = None,
        court: str = None,
        limit: int = 100,
        **kwargs,
    ) -> List[CaseData]:
        """
        Search for cases based on criteria.

        Args:
            query: Search query string
            start_date: Start date for search
            end_date: End date for search
            court: Specific court to search
            limit: Maximum number of results
            **kwargs: Additional search parameters

        Returns:
            List of CaseData objects
        """
        pass

    @abstractmethod
    def get_case_by_id(self, case_id: str) -> Optional[CaseData]:
        """
        Retrieve a specific case by its ID.

        Args:
            case_id: Unique case identifier

        Returns:
            CaseData object or None if not found
        """
        pass

    def get_recent_cases(
        self, days: int = 30, limit: int = 100, court: str = None
    ) -> List[CaseData]:
        """
        Get recent cases from the last N days.

        Args:
            days: Number of days to look back
            limit: Maximum number of results
            court: Specific court to search

        Returns:
            List of CaseData objects
        """
        from datetime import timedelta

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        return self.search_cases(
            start_date=start_date, end_date=end_date, limit=limit, court=court
        )

    def validate_search_params(
        self,
        start_date: Union[str, datetime] = None,
        end_date: Union[str, datetime] = None,
        limit: int = None,
    ) -> Dict[str, Any]:
        """
        Validate and normalize search parameters.

        Args:
            start_date: Start date for search
            end_date: End date for search
            limit: Maximum number of results

        Returns:
            Dictionary of validated parameters

        Raises:
            ValueError: If parameters are invalid
        """
        params = {}

        if start_date:
            params["start_date"] = validate_date(start_date)

        if end_date:
            params["end_date"] = validate_date(end_date)

        if params.get("start_date") and params.get("end_date"):
            if params["start_date"] > params["end_date"]:
                raise ValueError("Start date must be before end date")

        if limit is not None:
            if not isinstance(limit, int) or limit <= 0:
                raise ValueError("Limit must be a positive integer")
            params["limit"] = min(limit, 1000)  # Cap at reasonable limit

        return params

    def close(self):
        """Close the HTTP session."""
        if hasattr(self, "session"):
            self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
