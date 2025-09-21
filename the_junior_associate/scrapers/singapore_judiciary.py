"""
Singapore Judiciary scraper for The Junior Associate library.

Singapore Judiciary provides access to Singapore court decisions and legal information.
"""

import re
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from urllib.parse import urlencode, quote

from ..utils.base import BaseScraper
from ..utils.data_models import CaseData
from ..utils.exceptions import ParsingError, DataNotFoundError
from ..utils.helpers import sanitize_text, validate_date, normalize_court_name


class SingaporeJudiciaryScraper(BaseScraper):
    """
    Scraper for Singapore Judiciary website.

    Provides access to Singapore court decisions from the Supreme Court,
    State Courts, and Family Justice Courts.
    """

    @property
    def base_url(self) -> str:
        return "https://www.judiciary.gov.sg"

    @property
    def jurisdiction(self) -> str:
        return "Singapore"

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
        Search for cases on Singapore Judiciary website.

        Args:
            query: Search query string
            start_date: Start date for search (YYYY-MM-DD)
            end_date: End date for search (YYYY-MM-DD)
            court: Court type (e.g., 'Supreme Court', 'State Courts')
            limit: Maximum number of results (default: 100)
            **kwargs: Additional parameters like case_type

        Returns:
            List of CaseData objects

        Example:
            >>> scraper = SingaporeJudiciaryScraper()
            >>> cases = scraper.search_cases(
            ...     query="contract law",
            ...     start_date="2023-01-01",
            ...     court="Supreme Court",
            ...     limit=20
            ... )
        """
        # Validate parameters
        params = self.validate_search_params(start_date, end_date, limit)

        # Build search parameters
        search_params = {}

        if query:
            search_params["searchText"] = query

        if params.get("start_date"):
            search_params["startDate"] = params["start_date"].strftime("%Y-%m-%d")

        if params.get("end_date"):
            search_params["endDate"] = params["end_date"].strftime("%Y-%m-%d")

        if court:
            search_params["court"] = court

        case_type = kwargs.get("case_type")
        if case_type:
            search_params["caseType"] = case_type

        # Set results limit
        search_params["limit"] = min(params.get("limit", 100), 200)

        # Make request to search page
        url = f"{self.base_url}/judgment-search"

        try:
            response = self._make_request(url, params=search_params)
            soup = self._parse_html(response.text)
        except Exception as e:
            raise ParsingError(f"Failed to parse search results: {str(e)}")

        # Parse search results
        cases = []

        # Look for judgment links or case entries
        judgment_links = soup.find_all("a", href=re.compile(r"/judgment/"))

        for link in judgment_links[: params.get("limit", 100)]:
            try:
                case_data = self._parse_search_result_link(link)
                if case_data:
                    cases.append(case_data)
            except Exception as e:
                self.logger.warning(f"Failed to parse search result: {str(e)}")
                continue

        self.logger.info(f"Found {len(cases)} cases from Singapore Judiciary")
        return cases

    def get_case_by_id(self, case_id: str) -> Optional[CaseData]:
        """
        Retrieve a specific case by its case number or URL.

        Args:
            case_id: Singapore case number or URL

        Returns:
            CaseData object or None if not found

        Example:
            >>> scraper = SingaporeJudiciaryScraper()
            >>> case = scraper.get_case_by_id("[2023] SGCA 15")
        """
        if not case_id:
            raise ValueError("Case ID is required")

        # Determine URL format
        if case_id.startswith("http"):
            url = case_id
        elif case_id.startswith("[") and "]" in case_id:
            # Singapore citation format
            cases = self.search_cases(query=case_id, limit=1)
            if cases:
                return cases[0]
            return None
        else:
            # Try searching for the case number
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

            # Extract case ID from case name or URL
            case_id = ""
            citation_match = re.search(
                r"\[(\d{4})\]\s+(SGCA|SGHC|SGFC|SGMC)\s+(\d+)", case_name
            )
            if citation_match:
                case_id = f"[{citation_match.group(1)}] {citation_match.group(2)} {citation_match.group(3)}"

            # Basic case data from search result
            return CaseData(
                case_name=case_name,
                case_id=case_id,
                url=case_url,
                jurisdiction=self.jurisdiction,
                metadata={"source": "Singapore Judiciary"},
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
            court_name = ""
            case_date = None
            citations = []

            # Look for court information
            court_patterns = [
                r"(Court of Appeal|High Court|State Courts|Family Justice Courts)",
                r"(SGCA|SGHC|SGFC|SGMC|SGDC)",
            ]

            page_text = soup.get_text()
            for pattern in court_patterns:
                court_matches = re.findall(pattern, page_text, re.IGNORECASE)
                if court_matches:
                    court_name = normalize_court_name(court_matches[0])
                    break

            # Look for date patterns
            date_patterns = [
                r"(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})",
                r"(\d{4}-\d{2}-\d{2})",
                r"(\d{1,2}/\d{1,2}/\d{4})",
            ]

            for pattern in date_patterns:
                date_matches = re.findall(pattern, page_text)
                if date_matches:
                    try:
                        # Try different date formats
                        date_str = date_matches[0]
                        if "-" in date_str:
                            case_date = datetime.strptime(date_str, "%Y-%m-%d")
                        elif "/" in date_str:
                            case_date = datetime.strptime(date_str, "%d/%m/%Y")
                        else:
                            case_date = datetime.strptime(date_str, "%d %B %Y")
                        break
                    except ValueError:
                        continue

            # Extract citations
            citation_patterns = [
                r"\[(\d{4})\]\s+(SGCA|SGHC|SGFC|SGMC)\s+(\d+)",
                r"(\d{4})\s+(SGCA|SGHC|SGFC|SGMC)\s+(\d+)",
                r"\[(\d{4})\]\s+(\d+)\s+(SLR|MLJ)",
            ]

            for pattern in citation_patterns:
                citation_matches = re.findall(pattern, page_text)
                if citation_matches:
                    for match in citation_matches:
                        if len(match) == 3:
                            citations.append(f"[{match[0]}] {match[1]} {match[2]}")

            # Extract full text content
            full_text = ""
            # Look for main content area
            content_selectors = [
                "div.judgment-content",
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
                r"(?:Justice|Judge|JC)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
                r"([A-Z][a-z]+\s+JA)",
                r"([A-Z][a-z]+\s+J\.?)",
            ]

            for pattern in judge_patterns:
                judge_matches = re.findall(
                    pattern, full_text[:3000]
                )  # Look in first part
                judges.extend(
                    [
                        match.replace(" JA", "").replace(" J.", "").replace(" J", "")
                        for match in judge_matches
                    ]
                )

            judges = list(set(judges[:5]))  # Limit and dedupe

            # Extract case ID from citations or case name
            case_id = ""
            if citations:
                case_id = citations[0]
            else:
                citation_match = re.search(
                    r"\[(\d{4})\]\s+(SGCA|SGHC|SGFC|SGMC)\s+(\d+)", case_name
                )
                if citation_match:
                    case_id = f"[{citation_match.group(1)}] {citation_match.group(2)} {citation_match.group(3)}"

            # Extract parties
            parties = []
            party_pattern = r"([A-Z][a-z\s]+(?:Pte\s+Ltd|Ltd|Inc)?)\s+v\s+([A-Z][a-z\s]+(?:Pte\s+Ltd|Ltd|Inc)?)"
            party_matches = re.findall(party_pattern, case_name)
            if party_matches:
                for match in party_matches[0]:
                    if match.strip():
                        parties.append(match.strip())

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
                jurisdiction=self.jurisdiction,
                metadata={"source": "Singapore Judiciary"},
            )

        except Exception as e:
            self.logger.error(f"Error parsing case detail: {str(e)}")
            return None


# Convenience functions
def get_case_by_id(case_id: str) -> Optional[CaseData]:
    """
    Get a specific case by ID from Singapore Judiciary.

    Args:
        case_id: Singapore case citation

    Returns:
        CaseData object or None

    Example:
        >>> from the_junior_associate.singapore_judiciary import get_case_by_id
        >>> case = get_case_by_id("[2023] SGCA 15")
        >>> if case:
        ...     print(case.case_name)
    """
    with SingaporeJudiciaryScraper() as scraper:
        return scraper.get_case_by_id(case_id)


def search_cases(
    query: str,
    start_date: Union[str, datetime] = None,
    end_date: Union[str, datetime] = None,
    court: str = None,
    limit: int = 100,
) -> List[CaseData]:
    """
    Search for cases on Singapore Judiciary website.

    Args:
        query: Search query string
        start_date: Start date for search
        end_date: End date for search
        court: Court type
        limit: Maximum number of results

    Returns:
        List of CaseData objects

    Example:
        >>> from the_junior_associate.singapore_judiciary import search_cases
        >>> cases = search_cases("contract law", court="Supreme Court")
    """
    with SingaporeJudiciaryScraper() as scraper:
        return scraper.search_cases(
            query=query,
            start_date=start_date,
            end_date=end_date,
            court=court,
            limit=limit,
        )
