"""
Supreme Court of India scraper for The Junior Associate library.

Supreme Court of India provides access to judgments and orders from India's highest court.
"""

import re
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from urllib.parse import urlencode, quote

from ..utils.base import BaseScraper
from ..utils.data_models import CaseData
from ..utils.exceptions import ParsingError, DataNotFoundError
from ..utils.helpers import sanitize_text, validate_date, normalize_court_name


class SupremeCourtIndiaScraper(BaseScraper):
    """
    Scraper for Supreme Court of India website.

    Provides access to judgments, orders, and other decisions from
    the Supreme Court of India.
    """

    @property
    def base_url(self) -> str:
        return "https://main.sci.gov.in"

    @property
    def jurisdiction(self) -> str:
        return "India"

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
        Search for cases on Supreme Court of India website.

        Args:
            query: Search query string
            start_date: Start date for search (YYYY-MM-DD)
            end_date: End date for search (YYYY-MM-DD)
            court: Court name (defaults to "Supreme Court of India")
            limit: Maximum number of results (default: 100)
            **kwargs: Additional parameters like bench, case_type

        Returns:
            List of CaseData objects

        Example:
            >>> scraper = SupremeCourtIndiaScraper()
            >>> cases = scraper.search_cases(
            ...     query="fundamental rights",
            ...     start_date="2023-01-01",
            ...     limit=20
            ... )
        """
        # Validate parameters
        params = self.validate_search_params(start_date, end_date, limit)

        # Build search parameters
        search_params = {}

        if query:
            search_params["search_text"] = query

        if params.get("start_date"):
            search_params["from_date"] = params["start_date"].strftime("%d-%m-%Y")

        if params.get("end_date"):
            search_params["to_date"] = params["end_date"].strftime("%d-%m-%Y")

        # Additional parameters
        bench = kwargs.get("bench")
        if bench:
            search_params["bench"] = bench

        case_type = kwargs.get("case_type")
        if case_type:
            search_params["case_type"] = case_type

        # Set results limit
        search_params["limit"] = min(params.get("limit", 100), 200)

        # Make request to search page
        url = f"{self.base_url}/judgments"

        try:
            response = self._make_request(url, params=search_params)
            soup = self._parse_html(response.text)
        except Exception as e:
            raise ParsingError(f"Failed to parse search results: {str(e)}")

        # Parse search results
        cases = []

        # Look for judgment links in search results
        judgment_links = soup.find_all("a", href=re.compile(r"/judgment/"))

        for link in judgment_links[: params.get("limit", 100)]:
            try:
                case_data = self._parse_search_result_link(link)
                if case_data:
                    cases.append(case_data)
            except Exception as e:
                self.logger.warning(f"Failed to parse search result: {str(e)}")
                continue

        self.logger.info(f"Found {len(cases)} cases from Supreme Court of India")
        return cases

    def get_case_by_id(self, case_id: str) -> Optional[CaseData]:
        """
        Retrieve a specific case by its case number or URL.

        Args:
            case_id: Supreme Court case number or URL

        Returns:
            CaseData object or None if not found

        Example:
            >>> scraper = SupremeCourtIndiaScraper()
            >>> case = scraper.get_case_by_id("SLP (C) 12345/2023")
        """
        if not case_id:
            raise ValueError("Case ID is required")

        # Determine URL format
        if case_id.startswith("http"):
            url = case_id
        elif re.match(r"[A-Z]+\s*\([A-Z]\)\s*\d+/\d+", case_id):
            # Supreme Court case number format
            cases = self.search_cases(query=case_id, limit=1)
            if cases:
                return cases[0]
            return None
        else:
            # Try searching for the case
            cases = self.search_cases(query=case_id, limit=1)
            if cases:
                return cases[0]
            return None

        try:
            response = self._make_request(url)
            soup = self._parse_html(response.text)
            return self._parse_case_detail(soup, url)
        except Exception as e:
            self.logger.error(f"Failed to get case {case_id}: {str(e)}")
            return None

    def _parse_search_result_link(self, link) -> Optional[CaseData]:
        """Parse a search result link into CaseData."""
        try:
            case_name = sanitize_text(link.get_text())
            case_url = link.get("href")

            if case_url and not case_url.startswith("http"):
                case_url = f"{self.base_url}{case_url}"

            # Extract case ID from case name
            case_id = ""
            case_number_patterns = [
                r"([A-Z]+\s*\([A-Z]\)\s*\d+/\d+)",
                r"(SLP\s*\([A-Z]\)\s*No\.\s*\d+/\d+)",
                r"(Civil\s+Appeal\s+No\.\s*\d+/\d+)",
                r"(Criminal\s+Appeal\s+No\.\s*\d+/\d+)",
            ]

            for pattern in case_number_patterns:
                case_match = re.search(pattern, case_name, re.IGNORECASE)
                if case_match:
                    case_id = case_match.group(1)
                    break

            # Basic case data from search result
            return CaseData(
                case_name=case_name,
                case_id=case_id,
                court="Supreme Court of India",
                url=case_url,
                jurisdiction=self.jurisdiction,
                metadata={"source": "Supreme Court of India"},
            )

        except Exception as e:
            self.logger.error(f"Error parsing search result link: {str(e)}")
            return None

    def _parse_case_detail(self, soup, url: str) -> Optional[CaseData]:
        """Parse detailed case page into CaseData."""
        try:
            # Extract case name from title or heading
            case_name = ""
            title_elem = soup.find("title")
            if title_elem:
                case_name = sanitize_text(title_elem.get_text())

            # Try h1 if title doesn't work
            if not case_name:
                h1_elem = soup.find("h1")
                if h1_elem:
                    case_name = sanitize_text(h1_elem.get_text())

            # Extract court and date information
            court_name = "Supreme Court of India"
            case_date = None
            citations = []

            page_text = soup.get_text()

            # Look for date patterns
            date_patterns = [
                r"(\d{1,2}-\d{1,2}-\d{4})",
                r"(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})",
                r"(\d{4}-\d{2}-\d{2})",
            ]

            for pattern in date_patterns:
                date_matches = re.findall(pattern, page_text)
                if date_matches:
                    try:
                        # Try different date formats
                        date_str = date_matches[0]
                        if "-" in date_str and len(date_str.split("-")[0]) == 4:
                            case_date = datetime.strptime(date_str, "%Y-%m-%d")
                        elif "-" in date_str:
                            case_date = datetime.strptime(date_str, "%d-%m-%Y")
                        else:
                            case_date = datetime.strptime(date_str, "%d %B %Y")
                        break
                    except ValueError:
                        continue

            # Extract citations
            citation_patterns = [
                r"(\d{4})\s+(\d+)\s+(SCC|SCR)",
                r"\((\d{4})\)\s+(\d+)\s+(SCC|SCR)",
                r"AIR\s+(\d{4})\s+SC\s+(\d+)",
                r"JT\s+(\d{4})\s+(\d+)\s+SC\s+(\d+)",
            ]

            for pattern in citation_patterns:
                citation_matches = re.findall(pattern, page_text)
                if citation_matches:
                    for match in citation_matches:
                        if len(match) == 3:
                            citations.append(f"({match[0]}) {match[1]} {match[2]}")
                        elif len(match) == 2:
                            citations.append(f"AIR {match[0]} SC {match[1]}")

            # Extract full text content
            full_text = ""
            # Look for main content area
            content_selectors = [
                "div.judgment-content",
                "div.judgment-text",
                "div.content",
                "div#main",
                "div.main-content",
                "body",
            ]

            for selector in content_selectors:
                content_div = soup.select_one(selector)
                if content_div:
                    # Remove navigation and other non-content elements
                    for unwanted in content_div.find_all(
                        ["nav", "header", "footer", "script", "style"]
                    ):
                        unwanted.decompose()
                    full_text = sanitize_text(content_div.get_text())
                    break

            # Extract judges
            judges = []
            judge_patterns = [
                r"(?:Justice|J\.)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
                r"Hon\'ble\s+(?:Mr\.|Ms\.)\s+Justice\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
                r"([A-Z][a-z]+\s+J\.?)",
                r"Chief\s+Justice\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
            ]

            for pattern in judge_patterns:
                judge_matches = re.findall(
                    pattern, full_text[:3000]
                )  # Look in first part
                judges.extend(
                    [
                        match.replace(" J.", "").replace(" J", "")
                        for match in judge_matches
                    ]
                )

            judges = list(set(judges[:5]))  # Limit and dedupe

            # Extract case ID from case name or text
            case_id = ""
            case_number_patterns = [
                r"([A-Z]+\s*\([A-Z]\)\s*\d+/\d+)",
                r"(SLP\s*\([A-Z]\)\s*No\.\s*\d+/\d+)",
                r"(Civil\s+Appeal\s+No\.\s*\d+/\d+)",
                r"(Criminal\s+Appeal\s+No\.\s*\d+/\d+)",
            ]

            for pattern in case_number_patterns:
                case_match = re.search(pattern, case_name, re.IGNORECASE)
                if case_match:
                    case_id = case_match.group(1)
                    break

            # Extract parties
            parties = []
            party_patterns = [
                r"([A-Z][a-z\s]+(?:Ltd|Pvt\.\s+Ltd|Inc)?)\s+[Vv]\.\s+([A-Z][a-z\s]+(?:Ltd|Pvt\.\s+Ltd|Inc)?)",
                r"([A-Z][a-z\s]+)\s+vs?\.\s+([A-Z][a-z\s]+)",
            ]

            for pattern in party_patterns:
                party_matches = re.findall(pattern, case_name)
                if party_matches:
                    for match in party_matches[0]:
                        if match.strip():
                            parties.append(match.strip())
                    break

            # Extract case type
            case_type = ""
            type_patterns = [
                r"(Special Leave Petition|SLP)",
                r"(Civil Appeal|Criminal Appeal)",
                r"(Writ Petition|Original Jurisdiction)",
                r"(Transfer Petition|Review Petition)",
            ]

            for pattern in type_patterns:
                type_matches = re.findall(pattern, case_name, re.IGNORECASE)
                if type_matches:
                    case_type = type_matches[0]
                    break

            return CaseData(
                case_name=case_name,
                case_id=case_id,
                court=court_name,
                date=case_date,
                url=url,
                full_text=full_text,
                judges=judges,
                parties=parties,
                citations=citations,
                case_type=case_type,
                jurisdiction=self.jurisdiction,
                metadata={"source": "Supreme Court of India"},
            )

        except Exception as e:
            self.logger.error(f"Error parsing case detail: {str(e)}")
            return None


# Convenience functions
def get_case_by_id(case_id: str) -> Optional[CaseData]:
    """
    Get a specific case by ID from Supreme Court of India.

    Args:
        case_id: Supreme Court case number

    Returns:
        CaseData object or None

    Example:
        >>> from the_junior_associate.supremecourt_india import get_case_by_id
        >>> case = get_case_by_id("SLP (C) 12345/2023")
        >>> if case:
        ...     print(case.case_name)
    """
    with SupremeCourtIndiaScraper() as scraper:
        return scraper.get_case_by_id(case_id)


def search_cases(
    query: str,
    start_date: Union[str, datetime] = None,
    end_date: Union[str, datetime] = None,
    court: str = None,
    limit: int = 100,
) -> List[CaseData]:
    """
    Search for cases on Supreme Court of India website.

    Args:
        query: Search query string
        start_date: Start date for search
        end_date: End date for search
        court: Court name (ignored, always Supreme Court of India)
        limit: Maximum number of results

    Returns:
        List of CaseData objects

    Example:
        >>> from the_junior_associate.supremecourt_india import search_cases
        >>> cases = search_cases("fundamental rights")
    """
    with SupremeCourtIndiaScraper() as scraper:
        return scraper.search_cases(
            query=query,
            start_date=start_date,
            end_date=end_date,
            court=court,
            limit=limit,
        )
