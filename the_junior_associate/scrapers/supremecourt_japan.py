"""
Supreme Court of Japan scraper for The Junior Associate library.

Supreme Court of Japan provides access to Japanese court decisions.
"""

import re
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from urllib.parse import urlencode, quote

from ..utils.base import BaseScraper
from ..utils.data_models import CaseData
from ..utils.exceptions import ParsingError, DataNotFoundError
from ..utils.helpers import sanitize_text, validate_date, normalize_court_name


class SupremeCourtJapanScraper(BaseScraper):
    """
    Scraper for Supreme Court of Japan website.

    Provides access to judgments and decisions from the Supreme Court of Japan
    and other Japanese courts.
    """

    @property
    def base_url(self) -> str:
        return "https://www.courts.go.jp"

    @property
    def jurisdiction(self) -> str:
        return "Japan"

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
        Search for cases on Supreme Court of Japan website.

        Args:
            query: Search query string
            start_date: Start date for search (YYYY-MM-DD)
            end_date: End date for search (YYYY-MM-DD)
            court: Court name (defaults to "Supreme Court of Japan")
            limit: Maximum number of results (default: 100)
            **kwargs: Additional parameters like language ('ja', 'en')

        Returns:
            List of CaseData objects

        Example:
            >>> scraper = SupremeCourtJapanScraper()
            >>> cases = scraper.search_cases(
            ...     query="constitutional",
            ...     start_date="2023-01-01",
            ...     limit=20
            ... )
        """
        # Validate parameters
        params = self.validate_search_params(start_date, end_date, limit)

        # Build search parameters
        search_params = {}

        if query:
            search_params["q"] = query

        if params.get("start_date"):
            search_params["start_date"] = params["start_date"].strftime("%Y-%m-%d")

        if params.get("end_date"):
            search_params["end_date"] = params["end_date"].strftime("%Y-%m-%d")

        # Language preference
        language = kwargs.get("language", "en")
        if language in ["ja", "en"]:
            search_params["lang"] = language

        # Set results limit
        search_params["limit"] = min(params.get("limit", 100), 200)

        # Make request to search page
        url = f"{self.base_url}/app/hanrei_en/search"

        try:
            response = self._make_request(url, params=search_params)
            soup = self._parse_html(response.text)
        except Exception as e:
            raise ParsingError(f"Failed to parse search results: {str(e)}")

        # Parse search results
        cases = []

        # Look for judgment links in search results
        judgment_links = soup.find_all("a", href=re.compile(r"/app/hanrei_en/detail"))

        for link in judgment_links[: params.get("limit", 100)]:
            try:
                case_data = self._parse_search_result_link(link)
                if case_data:
                    cases.append(case_data)
            except Exception as e:
                self.logger.warning(f"Failed to parse search result: {str(e)}")
                continue

        self.logger.info(f"Found {len(cases)} cases from Supreme Court of Japan")
        return cases

    def get_case_by_id(self, case_id: str) -> Optional[CaseData]:
        """
        Retrieve a specific case by its case number or URL.

        Args:
            case_id: Japanese case number or URL

        Returns:
            CaseData object or None if not found

        Example:
            >>> scraper = SupremeCourtJapanScraper()
            >>> case = scraper.get_case_by_id("平成31年(行ツ)123")
        """
        if not case_id:
            raise ValueError("Case ID is required")

        # Determine URL format
        if case_id.startswith("http"):
            url = case_id
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

            # Extract case ID from URL or case name
            case_id = ""
            if case_url:
                case_id_match = re.search(r"id=([^&]+)", case_url)
                if case_id_match:
                    case_id = case_id_match.group(1)

            # If no ID from URL, try to extract from case name
            if not case_id:
                # Japanese case number patterns
                jp_case_patterns = [
                    r"(平成\d+年\([^)]+\)\d+)",
                    r"(令和\d+年\([^)]+\)\d+)",
                    r"(昭和\d+年\([^)]+\)\d+)",
                ]

                for pattern in jp_case_patterns:
                    case_match = re.search(pattern, case_name)
                    if case_match:
                        case_id = case_match.group(1)
                        break

            # Basic case data from search result
            return CaseData(
                case_name=case_name,
                case_id=case_id,
                court="Supreme Court of Japan",
                url=case_url,
                jurisdiction=self.jurisdiction,
                metadata={"source": "Supreme Court of Japan"},
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
            court_name = "Supreme Court of Japan"
            case_date = None
            citations = []

            page_text = soup.get_text()

            # Look for date patterns (both Western and Japanese dates)
            date_patterns = [
                r"(\d{4})年(\d{1,2})月(\d{1,2})日",  # Japanese date format
                r"(\d{4}-\d{2}-\d{2})",
                r"(\d{1,2}/\d{1,2}/\d{4})",
            ]

            for pattern in date_patterns:
                date_matches = re.findall(pattern, page_text)
                if date_matches:
                    try:
                        # Try different date formats
                        date_match = date_matches[0]
                        if len(date_match) == 3:  # Japanese format
                            year, month, day = date_match
                            case_date = datetime(int(year), int(month), int(day))
                        elif "-" in date_match:
                            case_date = datetime.strptime(date_match, "%Y-%m-%d")
                        elif "/" in date_match:
                            case_date = datetime.strptime(date_match, "%d/%m/%Y")
                        break
                    except ValueError:
                        continue

            # Extract case numbers and citations
            citation_patterns = [
                r"(平成\d+年\([^)]+\)\d+)",
                r"(令和\d+年\([^)]+\)\d+)",
                r"(昭和\d+年\([^)]+\)\d+)",
                r"(最高裁判所第[一二三]小法廷)",
                r"(最高裁判所大法廷)",
            ]

            for pattern in citation_patterns:
                citation_matches = re.findall(pattern, page_text)
                if citation_matches:
                    citations.extend(citation_matches)

            # Extract full text content
            full_text = ""
            # Look for main content area
            content_selectors = [
                "div.judgment-content",
                "div.hanrei-content",
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

            # Extract judges (裁判官)
            judges = []
            judge_patterns = [
                r"裁判官\s*([^\s]+)",
                r"裁判長\s*([^\s]+)",
                r"Justice\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
                r"Chief\s+Justice\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
            ]

            for pattern in judge_patterns:
                judge_matches = re.findall(
                    pattern, full_text[:3000]
                )  # Look in first part
                judges.extend(judge_matches)

            judges = list(set(judges[:5]))  # Limit and dedupe

            # Extract case ID from URL or citations
            case_id = ""
            if case_url:
                case_id_match = re.search(r"id=([^&]+)", case_url)
                if case_id_match:
                    case_id = case_id_match.group(1)

            # If no ID from URL, use first citation
            if not case_id and citations:
                case_id = citations[0]

            # Extract parties (when available in English cases)
            parties = []
            party_patterns = [
                r"([A-Z][a-z\s]+(?:Co\.|Corp\.|Ltd\.)?)\s+v\.?\s+([A-Z][a-z\s]+(?:Co\.|Corp\.|Ltd\.)?)",
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
                r"(行政事件|民事事件|刑事事件)",  # Administrative/Civil/Criminal cases
                r"(Appeal|Petition|Application)",
                r"(Constitutional|Administrative|Civil|Criminal)",
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
                metadata={"source": "Supreme Court of Japan"},
            )

        except Exception as e:
            self.logger.error(f"Error parsing case detail: {str(e)}")
            return None


# Convenience functions
def get_case_by_id(case_id: str) -> Optional[CaseData]:
    """
    Get a specific case by ID from Supreme Court of Japan.

    Args:
        case_id: Japanese case number

    Returns:
        CaseData object or None

    Example:
        >>> from the_junior_associate.supremecourt_japan import get_case_by_id
        >>> case = get_case_by_id("平成31年(行ツ)123")
        >>> if case:
        ...     print(case.case_name)
    """
    with SupremeCourtJapanScraper() as scraper:
        return scraper.get_case_by_id(case_id)


def search_cases(
    query: str,
    start_date: Union[str, datetime] = None,
    end_date: Union[str, datetime] = None,
    court: str = None,
    limit: int = 100,
) -> List[CaseData]:
    """
    Search for cases on Supreme Court of Japan website.

    Args:
        query: Search query string
        start_date: Start date for search
        end_date: End date for search
        court: Court name (ignored, always Supreme Court of Japan)
        limit: Maximum number of results

    Returns:
        List of CaseData objects

    Example:
        >>> from the_junior_associate.supremecourt_japan import search_cases
        >>> cases = search_cases("constitutional")
    """
    with SupremeCourtJapanScraper() as scraper:
        return scraper.search_cases(
            query=query,
            start_date=start_date,
            end_date=end_date,
            court=court,
            limit=limit,
        )
