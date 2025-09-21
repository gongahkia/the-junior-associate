"""
FindLaw scraper for The Junior Associate library.

FindLaw provides access to US Supreme Court and state case law collection.
"""

import re
from datetime import datetime
from typing import List, Optional, Dict, Any, Union

from ..utils.base import BaseScraper
from ..utils.data_models import CaseData
from ..utils.exceptions import ParsingError
from ..utils.helpers import sanitize_text, validate_date, normalize_court_name


class FindLawScraper(BaseScraper):
    """
    Scraper for FindLaw.com - US Supreme Court and state case law collection.
    """

    @property
    def base_url(self) -> str:
        return "https://caselaw.findlaw.com"

    @property
    def jurisdiction(self) -> str:
        return "United States"

    def search_cases(
        self,
        query: str = None,
        start_date: Union[str, datetime] = None,
        end_date: Union[str, datetime] = None,
        court: str = None,
        limit: int = 100,
        **kwargs,
    ) -> List[CaseData]:
        """Search for cases on FindLaw."""
        params = self.validate_search_params(start_date, end_date, limit)

        search_params = {}
        if query:
            search_params["q"] = query

        url = f"{self.base_url}/us-supreme-court/"
        if court and court.lower() != "supreme":
            url = f"{self.base_url}/state/"

        try:
            response = self._make_request(url, params=search_params)
            soup = self._parse_html(response.text)
        except Exception as e:
            raise ParsingError(f"Failed to parse search results: {str(e)}")

        cases = []
        case_links = soup.find_all("a", href=re.compile(r"/case/"))

        for link in case_links[: params.get("limit", 100)]:
            try:
                case_url = link.get("href")
                if not case_url.startswith("http"):
                    case_url = f"{self.base_url}{case_url}"

                case_data = self._scrape_case_from_url(case_url)
                if case_data:
                    cases.append(case_data)
            except Exception as e:
                self.logger.warning(f"Failed to parse case: {str(e)}")
                continue

        return cases

    def get_case_by_id(self, case_id: str) -> Optional[CaseData]:
        """Retrieve a specific case by its FindLaw ID."""
        if not case_id:
            raise ValueError("Case ID is required")

        url = f"{self.base_url}/case/{case_id}"
        return self._scrape_case_from_url(url)

    def _scrape_case_from_url(self, url: str) -> Optional[CaseData]:
        """Scrape case data from a FindLaw case URL."""
        try:
            response = self._make_request(url)
            soup = self._parse_html(response.text)

            # Extract case name
            case_name = ""
            title_elem = soup.find("h1") or soup.find("title")
            if title_elem:
                case_name = sanitize_text(title_elem.get_text())

            # Extract case details
            court_name = "FindLaw"
            case_date = None
            full_text = ""

            # Try to extract content
            content_div = soup.find("div", class_="content") or soup.find("main")
            if content_div:
                full_text = sanitize_text(content_div.get_text())

            # Extract case ID from URL
            case_id = re.search(r"/case/([^/]+)", url)
            case_id = case_id.group(1) if case_id else ""

            return CaseData(
                case_name=case_name,
                case_id=case_id,
                court=court_name,
                date=case_date,
                url=url,
                full_text=full_text,
                jurisdiction=self.jurisdiction,
                metadata={"source": "FindLaw"},
            )

        except Exception as e:
            self.logger.error(f"Error scraping case from {url}: {str(e)}")
            return None
