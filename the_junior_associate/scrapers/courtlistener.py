"""
CourtListener scraper for The Junior Associate library.

CourtListener is a free law project providing access to US federal and state
case law, with comprehensive coverage and search capabilities.
"""

import json
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from urllib.parse import urlencode

from ..utils.base import BaseScraper
from ..utils.data_models import CaseData
from ..utils.exceptions import ParsingError, DataNotFoundError
from ..utils.helpers import sanitize_text, validate_date


class CourtListenerScraper(BaseScraper):
    """
    Scraper for CourtListener.com - Free US federal and state case law database.

    CourtListener provides both a web interface and REST API for accessing
    millions of legal documents from US courts at all levels.
    """

    @property
    def base_url(self) -> str:
        return "https://www.courtlistener.com"

    @property
    def jurisdiction(self) -> str:
        return "United States"

    def search_cases(
        self,
        query: Optional[str] = None,
        start_date: Optional[Union[str, datetime]] = None,
        end_date: Optional[Union[str, datetime]] = None,
        court: Optional[str] = None,
        limit: int = 100,
        **kwargs,
    ) -> List[CaseData]:
        """
        Search for cases on CourtListener.

        Args:
            query: Search query string
            start_date: Start date for search (YYYY-MM-DD)
            end_date: End date for search (YYYY-MM-DD)
            court: Court identifier or name
            limit: Maximum number of results (default: 100, max: 1000)
            **kwargs: Additional parameters like judge, case_name, citation

        Returns:
            List of CaseData objects

        Example:
            >>> scraper = CourtListenerScraper()
            >>> cases = scraper.search_cases(
            ...     query="privacy rights",
            ...     start_date="2023-01-01",
            ...     court="scotus",
            ...     limit=10
            ... )
        """
        # Validate parameters
        params = self.validate_search_params(start_date, end_date, limit)

        # Build search parameters
        search_params = {
            "format": "json",
            "order_by": "-date_filed",
        }

        if query:
            search_params["q"] = query

        if params.get("start_date"):
            search_params["filed_after"] = params["start_date"].strftime("%Y-%m-%d")

        if params.get("end_date"):
            search_params["filed_before"] = params["end_date"].strftime("%Y-%m-%d")

        if court:
            search_params["court"] = court

        if params.get("limit"):
            search_params["count"] = min(params["limit"], 1000)

        # Additional search parameters
        for key, value in kwargs.items():
            if key in ["judge", "case_name", "citation", "status"] and value:
                search_params[key] = value

        # Make API request
        url = f"{self.base_url}/api/rest/v3/search/"

        try:
            response = self._make_request(url, params=search_params)
            data = response.json()
        except json.JSONDecodeError as e:
            raise ParsingError(f"Failed to parse JSON response: {str(e)}")

        # Parse results
        cases = []
        results = data.get("results", [])

        for item in results:
            try:
                case_data = self._parse_search_result(item)
                if case_data:
                    cases.append(case_data)
            except Exception as e:
                self.logger.warning(f"Failed to parse search result: {str(e)}")
                continue

        self.logger.info(f"Found {len(cases)} cases from CourtListener")
        return cases

    def get_case_by_id(self, case_id: str) -> Optional[CaseData]:
        """
        Retrieve a specific case by its CourtListener ID.

        Args:
            case_id: CourtListener opinion ID or cluster ID

        Returns:
            CaseData object or None if not found

        Example:
            >>> scraper = CourtListenerScraper()
            >>> case = scraper.get_case_by_id("12345")
        """
        if not case_id:
            raise ValueError("Case ID is required")

        # Try opinion endpoint first
        url = f"{self.base_url}/api/rest/v3/opinions/{case_id}/"

        try:
            response = self._make_request(url, params={"format": "json"})
            data = response.json()
            return self._parse_opinion_detail(data)
        except Exception as e:
            self.logger.debug(f"Failed to get opinion {case_id}: {str(e)}")

        # Try cluster endpoint
        url = f"{self.base_url}/api/rest/v3/clusters/{case_id}/"

        try:
            response = self._make_request(url, params={"format": "json"})
            data = response.json()
            return self._parse_cluster_detail(data)
        except Exception as e:
            self.logger.error(f"Failed to get case {case_id}: {str(e)}")
            return None

    def get_recent_cases(
        self, days: int = 30, limit: int = 100, court: str = None
    ) -> List[CaseData]:
        """
        Get recent cases from CourtListener.

        Args:
            days: Number of days to look back (default: 30)
            limit: Maximum number of results (default: 100)
            court: Specific court to filter by

        Returns:
            List of CaseData objects

        Example:
            >>> scraper = CourtListenerScraper()
            >>> recent = scraper.get_recent_cases(days=7, court="scotus")
        """
        from datetime import timedelta

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        return self.search_cases(
            start_date=start_date, end_date=end_date, limit=limit, court=court
        )

    def _parse_search_result(self, item: Dict[str, Any]) -> Optional[CaseData]:
        """Parse a search result item into CaseData."""
        try:
            # Extract basic information
            case_name = sanitize_text(item.get("caseName", ""))
            if not case_name:
                return None

            # Parse date
            date_filed = None
            if item.get("dateFiled"):
                try:
                    date_filed = datetime.strptime(item["dateFiled"], "%Y-%m-%d")
                except ValueError:
                    pass

            # Extract court information
            court_name = sanitize_text(item.get("court", ""))

            # Build case URL
            case_url = None
            if item.get("absolute_url"):
                case_url = f"{self.base_url}{item['absolute_url']}"

            # Extract citations
            citations = []
            if item.get("citation"):
                citations = [item["citation"]]

            # Extract judges
            judges = []
            if item.get("judge"):
                judges = [sanitize_text(item["judge"])]

            # Create CaseData object
            return CaseData(
                case_name=case_name,
                case_id=str(item.get("id", "")),
                court=court_name,
                date=date_filed,
                url=case_url,
                summary=sanitize_text(item.get("snippet", "")),
                judges=judges,
                citations=citations,
                jurisdiction=self.jurisdiction,
                case_type=sanitize_text(item.get("status", "")),
                metadata={"source": "CourtListener", "api_data": item},
            )

        except Exception as e:
            self.logger.error(f"Error parsing search result: {str(e)}")
            return None

    def _parse_opinion_detail(self, data: Dict[str, Any]) -> Optional[CaseData]:
        """Parse detailed opinion data into CaseData."""
        try:
            # Get cluster information
            cluster_url = data.get("cluster")
            if cluster_url:
                # Fetch cluster details
                response = self._make_request(cluster_url, params={"format": "json"})
                cluster_data = response.json()

                case_name = sanitize_text(cluster_data.get("case_name", ""))

                # Parse date
                date_filed = None
                if cluster_data.get("date_filed"):
                    try:
                        date_filed = datetime.strptime(
                            cluster_data["date_filed"], "%Y-%m-%d"
                        )
                    except ValueError:
                        pass

                # Extract court
                court_name = sanitize_text(cluster_data.get("court", ""))

                # Extract citations
                citations = []
                for citation in cluster_data.get("citations", []):
                    if isinstance(citation, dict):
                        cite_text = citation.get("cite", "")
                    else:
                        cite_text = str(citation)
                    if cite_text:
                        citations.append(cite_text)

                # Extract judges
                judges = []
                if cluster_data.get("judges"):
                    for judge in cluster_data["judges"]:
                        if isinstance(judge, dict):
                            judge_name = judge.get("name_full", "")
                        else:
                            judge_name = str(judge)
                        if judge_name:
                            judges.append(sanitize_text(judge_name))

                # Get opinion text
                full_text = sanitize_text(
                    data.get("plain_text", "") or data.get("html", "")
                )

                return CaseData(
                    case_name=case_name,
                    case_id=str(data.get("id", "")),
                    court=court_name,
                    date=date_filed,
                    url=f"{self.base_url}{cluster_data.get('absolute_url', '')}",
                    full_text=full_text,
                    judges=judges,
                    citations=citations,
                    jurisdiction=self.jurisdiction,
                    metadata={
                        "source": "CourtListener",
                        "cluster_id": cluster_data.get("id"),
                        "opinion_type": data.get("type"),
                        "api_data": data,
                    },
                )

        except Exception as e:
            self.logger.error(f"Error parsing opinion detail: {str(e)}")
            return None

    def _parse_cluster_detail(self, data: Dict[str, Any]) -> Optional[CaseData]:
        """Parse cluster detail data into CaseData."""
        try:
            case_name = sanitize_text(data.get("case_name", ""))
            if not case_name:
                return None

            # Parse date
            date_filed = None
            if data.get("date_filed"):
                try:
                    date_filed = datetime.strptime(data["date_filed"], "%Y-%m-%d")
                except ValueError:
                    pass

            # Extract court
            court_name = sanitize_text(data.get("court", ""))

            # Extract citations
            citations = []
            for citation in data.get("citations", []):
                if isinstance(citation, dict):
                    cite_text = citation.get("cite", "")
                else:
                    cite_text = str(citation)
                if cite_text:
                    citations.append(cite_text)

            # Extract judges
            judges = []
            if data.get("judges"):
                for judge in data["judges"]:
                    if isinstance(judge, dict):
                        judge_name = judge.get("name_full", "")
                    else:
                        judge_name = str(judge)
                    if judge_name:
                        judges.append(sanitize_text(judge_name))

            return CaseData(
                case_name=case_name,
                case_id=str(data.get("id", "")),
                court=court_name,
                date=date_filed,
                url=f"{self.base_url}{data.get('absolute_url', '')}",
                summary=sanitize_text(data.get("headnotes", "")),
                judges=judges,
                citations=citations,
                jurisdiction=self.jurisdiction,
                metadata={
                    "source": "CourtListener",
                    "cluster_id": data.get("id"),
                    "api_data": data,
                },
            )

        except Exception as e:
            self.logger.error(f"Error parsing cluster detail: {str(e)}")
            return None


# Convenience functions for backward compatibility and ease of use
def fetch_recent_cases(
    start_date: Union[str, datetime] = None, limit: int = 100, court: str = None
) -> List[CaseData]:
    """
    Fetch recent cases from CourtListener.

    Args:
        start_date: Start date for search (default: 30 days ago)
        limit: Maximum number of results (default: 100)
        court: Specific court to filter by

    Returns:
        List of CaseData objects

    Example:
        >>> from the_junior_associate.courtlistener import fetch_recent_cases
        >>> cases = fetch_recent_cases(start_date="2023-01-01")
        >>> for case in cases:
        ...     print(case.case_name, case.date, case.url)
    """
    with CourtListenerScraper() as scraper:
        if start_date:
            end_date = datetime.now()
            return scraper.search_cases(
                start_date=start_date, end_date=end_date, limit=limit, court=court
            )
        else:
            return scraper.get_recent_cases(days=30, limit=limit, court=court)


def search_cases(
    query: str,
    start_date: Union[str, datetime] = None,
    end_date: Union[str, datetime] = None,
    limit: int = 100,
) -> List[CaseData]:
    """
    Search for cases on CourtListener.

    Args:
        query: Search query string
        start_date: Start date for search
        end_date: End date for search
        limit: Maximum number of results

    Returns:
        List of CaseData objects

    Example:
        >>> from the_junior_associate.courtlistener import search_cases
        >>> cases = search_cases("privacy rights", limit=50)
    """
    with CourtListenerScraper() as scraper:
        return scraper.search_cases(
            query=query, start_date=start_date, end_date=end_date, limit=limit
        )


def get_case_by_id(case_id: str) -> Optional[CaseData]:
    """
    Get a specific case by ID from CourtListener.

    Args:
        case_id: CourtListener case ID

    Returns:
        CaseData object or None

    Example:
        >>> from the_junior_associate.courtlistener import get_case_by_id
        >>> case = get_case_by_id("12345")
        >>> if case:
        ...     print(case.case_name)
    """
    with CourtListenerScraper() as scraper:
        return scraper.get_case_by_id(case_id)
