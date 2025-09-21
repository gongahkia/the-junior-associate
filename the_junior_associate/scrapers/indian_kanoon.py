"""
Indian Kanoon scraper for The Junior Associate library.

Indian Kanoon provides free access to Indian court judgments and legal documents.
"""

import re
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from urllib.parse import urlencode, quote

from ..utils.base import BaseScraper
from ..utils.data_models import CaseData
from ..utils.exceptions import ParsingError, DataNotFoundError
from ..utils.helpers import sanitize_text, validate_date, normalize_court_name


class IndianKanoonScraper(BaseScraper):
    """
    Scraper for IndianKanoon.org - Free Indian legal database.

    Indian Kanoon provides access to judgments from the Supreme Court of India,
    High Courts, and various tribunals and lower courts.
    """

    @property
    def base_url(self) -> str:
        return "https://indiankanoon.org"

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
        Search for cases on Indian Kanoon.

        Args:
            query: Search query string
            start_date: Start date for search (YYYY-MM-DD)
            end_date: End date for search (YYYY-MM-DD)
            court: Court name (e.g., 'Supreme Court', 'Delhi High Court')
            limit: Maximum number of results (default: 100)
            **kwargs: Additional parameters like author, bench

        Returns:
            List of CaseData objects

        Example:
            >>> scraper = IndianKanoonScraper()
            >>> cases = scraper.search_cases(
            ...     query="fundamental rights",
            ...     start_date="2023-01-01",
            ...     court="Supreme Court",
            ...     limit=20
            ... )
        """
        # Validate parameters
        params = self.validate_search_params(start_date, end_date, limit)

        # Build search parameters for Indian Kanoon
        search_params = {}

        if query:
            search_params["formInput"] = query

        if params.get("start_date"):
            search_params["from_date"] = params["start_date"].strftime("%d-%m-%Y")

        if params.get("end_date"):
            search_params["to_date"] = params["end_date"].strftime("%d-%m-%Y")

        if court:
            search_params["court"] = court

        # Additional parameters
        author = kwargs.get("author")
        if author:
            search_params["author"] = author

        bench = kwargs.get("bench")
        if bench:
            search_params["bench"] = bench

        # Set results limit
        search_params["limit"] = min(params.get("limit", 100), 200)

        # Make request to search page
        url = f"{self.base_url}/search/"

        try:
            response = self._make_request(url, params=search_params)
            soup = self._parse_html(response.text)
        except Exception as e:
            raise ParsingError(f"Failed to parse search results: {str(e)}")

        # Parse search results
        cases = []

        # Look for judgment links in search results
        result_divs = soup.find_all("div", class_="result")

        for result_div in result_divs[: params.get("limit", 100)]:
            try:
                case_data = self._parse_search_result(result_div)
                if case_data:
                    cases.append(case_data)
            except Exception as e:
                self.logger.warning(f"Failed to parse search result: {str(e)}")
                continue

        self.logger.info(f"Found {len(cases)} cases from Indian Kanoon")
        return cases

    def get_case_by_id(self, case_id: str) -> Optional[CaseData]:
        """
        Retrieve a specific case by its case number or URL.

        Args:
            case_id: Indian Kanoon case ID or URL

        Returns:
            CaseData object or None if not found

        Example:
            >>> scraper = IndianKanoonScraper()
            >>> case = scraper.get_case_by_id("1234567")
        """
        if not case_id:
            raise ValueError("Case ID is required")

        # Determine URL format
        if case_id.startswith("http"):
            url = case_id
        elif case_id.isdigit():
            # Indian Kanoon document ID
            url = f"{self.base_url}/doc/{case_id}/"
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

    def _parse_search_result(self, result_div) -> Optional[CaseData]:
        """Parse a search result div into CaseData."""
        try:
            # Extract case name from result title
            case_name = ""
            title_link = result_div.find("a", class_="result_title")
            if title_link:
                case_name = sanitize_text(title_link.get_text())
                case_url = title_link.get("href")
                if case_url and not case_url.startswith("http"):
                    case_url = f"{self.base_url}{case_url}"
            else:
                return None

            # Extract meta information
            court_name = ""
            case_date = None
            citations = []

            meta_div = result_div.find("div", class_="result_meta")
            if meta_div:
                meta_text = sanitize_text(meta_div.get_text())

                # Extract court from meta text
                court_match = re.search(r"Court:\s*([^,\n]+)", meta_text, re.IGNORECASE)
                if court_match:
                    court_name = normalize_court_name(court_match.group(1))

                # Extract date
                date_match = re.search(r"(\d{1,2}-\d{1,2}-\d{4})", meta_text)
                if date_match:
                    try:
                        case_date = datetime.strptime(date_match.group(1), "%d-%m-%Y")
                    except ValueError:
                        pass

                # Extract citations
                citation_matches = re.findall(
                    r"(\d{4})\s+(\d+)\s+(SCC|SCR|AIR)", meta_text
                )
                for match in citation_matches:
                    citations.append(f"({match[0]}) {match[1]} {match[2]}")

            # Extract case ID from URL
            case_id = ""
            if case_url:
                case_id_match = re.search(r"/doc/(\d+)/", case_url)
                if case_id_match:
                    case_id = case_id_match.group(1)

            # Extract summary if available
            summary = ""
            summary_div = result_div.find("div", class_="result_summary")
            if summary_div:
                summary = sanitize_text(summary_div.get_text())

            return CaseData(
                case_name=case_name,
                case_id=case_id,
                court=court_name,
                date=case_date,
                url=case_url,
                summary=summary,
                citations=citations,
                jurisdiction=self.jurisdiction,
                metadata={"source": "Indian Kanoon"},
            )

        except Exception as e:
            self.logger.error(f"Error parsing search result: {str(e)}")
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
                r"(Supreme Court of India|High Court|District Court|Tribunal)",
                r"(Delhi High Court|Bombay High Court|Calcutta High Court|Madras High Court)",
                r"(ITAT|CESTAT|CAT|NGT)",
            ]

            page_text = soup.get_text()
            for pattern in court_patterns:
                court_matches = re.findall(pattern, page_text, re.IGNORECASE)
                if court_matches:
                    court_name = normalize_court_name(court_matches[0])
                    break

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
                r"(\d{4})\s+(\d+)\s+(SCC|SCR|AIR)",
                r"\((\d{4})\)\s+(\d+)\s+(SCC|SCR|AIR)",
                r"AIR\s+(\d{4})\s+(SC|SCR)\s+(\d+)",
            ]

            for pattern in citation_patterns:
                citation_matches = re.findall(pattern, page_text)
                if citation_matches:
                    for match in citation_matches:
                        if len(match) == 3:
                            citations.append(f"({match[0]}) {match[1]} {match[2]}")

            # Extract full text content
            full_text = ""
            # Look for main content area
            content_selectors = [
                "div.judgment_text",
                "div.doc_text",
                "div#content",
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

            # Extract case ID from URL
            case_id = ""
            case_id_match = re.search(r"/doc/(\d+)/", url)
            if case_id_match:
                case_id = case_id_match.group(1)

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
                metadata={"source": "Indian Kanoon"},
            )

        except Exception as e:
            self.logger.error(f"Error parsing case detail: {str(e)}")
            return None


# Convenience functions
def get_case_by_id(case_id: str) -> Optional[CaseData]:
    """
    Get a specific case by ID from Indian Kanoon.

    Args:
        case_id: Indian Kanoon document ID

    Returns:
        CaseData object or None

    Example:
        >>> from the_junior_associate.indian_kanoon import get_case_by_id
        >>> case = get_case_by_id("1234567")
        >>> if case:
        ...     print(case.case_name)
    """
    with IndianKanoonScraper() as scraper:
        return scraper.get_case_by_id(case_id)


def search_cases(
    query: str,
    start_date: Union[str, datetime] = None,
    end_date: Union[str, datetime] = None,
    court: str = None,
    limit: int = 100,
) -> List[CaseData]:
    """
    Search for cases on Indian Kanoon.

    Args:
        query: Search query string
        start_date: Start date for search
        end_date: End date for search
        court: Court name
        limit: Maximum number of results

    Returns:
        List of CaseData objects

    Example:
        >>> from the_junior_associate.indian_kanoon import search_cases
        >>> cases = search_cases("fundamental rights", court="Supreme Court")
    """
    with IndianKanoonScraper() as scraper:
        return scraper.search_cases(
            query=query,
            start_date=start_date,
            end_date=end_date,
            court=court,
            limit=limit,
        )
