"""
CanLII scraper for The Junior Associate library.

CanLII is the Canadian Legal Information Institute providing free access
to Canadian federal and provincial case law and legislation.
"""

import re
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from urllib.parse import urlencode, quote

from ..utils.base import BaseScraper
from ..utils.data_models import CaseData
from ..utils.exceptions import ParsingError, DataNotFoundError
from ..utils.helpers import sanitize_text, validate_date, normalize_court_name


class CanLIIScraper(BaseScraper):
    """
    Scraper for CanLII.org - Canadian Legal Information Institute.

    CanLII provides comprehensive access to Canadian case law from federal,
    provincial, and territorial courts and tribunals.
    """

    @property
    def base_url(self) -> str:
        return "https://www.canlii.org"

    @property
    def jurisdiction(self) -> str:
        return "Canada"

    def search_cases(
        self,
        query: str = None,
        start_date: Union[str, datetime] = None,
        end_date: Union[str, datetime] = None,
        court: str = None,
        limit: int = 100,
        **kwargs
    ) -> List[CaseData]:
        """
        Search for cases on CanLII.

        Args:
            query: Search query string
            start_date: Start date for search (YYYY-MM-DD)
            end_date: End date for search (YYYY-MM-DD)
            court: Court or tribunal code (e.g., 'scc-csc', 'onca')
            limit: Maximum number of results (default: 100)
            **kwargs: Additional parameters like language ('en' or 'fr')

        Returns:
            List of CaseData objects

        Example:
            >>> scraper = CanLIIScraper()
            >>> cases = scraper.search_cases(
            ...     query="charter rights",
            ...     start_date="2023-01-01",
            ...     court="scc-csc",
            ...     limit=20
            ... )
        """
        # Validate parameters
        params = self.validate_search_params(start_date, end_date, limit)

        # Build search URL and parameters
        search_params = {
            'resultCount': min(params.get('limit', 100), 200),  # CanLII limit
            'sort': 'decisionDateDesc'
        }

        if query:
            search_params['text'] = query

        if params.get('start_date'):
            search_params['dateFrom'] = params['start_date'].strftime('%Y-%m-%d')

        if params.get('end_date'):
            search_params['dateTo'] = params['end_date'].strftime('%Y-%m-%d')

        if court:
            search_params['tribunal'] = court

        # Language preference
        language = kwargs.get('language', 'en')
        if language in ['en', 'fr']:
            search_params['language'] = language

        # Make request to search page
        url = f"{self.base_url}/{language}/search/"

        try:
            response = self._make_request(url, params=search_params)
            soup = self._parse_html(response.text)
        except Exception as e:
            raise ParsingError(f"Failed to parse search results: {str(e)}")

        # Parse search results
        cases = []
        results = soup.find_all('div', class_='result')

        for result in results[:params.get('limit', 100)]:
            try:
                case_data = self._parse_search_result(result, language)
                if case_data:
                    cases.append(case_data)
            except Exception as e:
                self.logger.warning(f"Failed to parse search result: {str(e)}")
                continue

        self.logger.info(f"Found {len(cases)} cases from CanLII")
        return cases

    def get_case_by_id(self, case_id: str) -> Optional[CaseData]:
        """
        Retrieve a specific case by its CanLII citation or URL path.

        Args:
            case_id: CanLII case citation (e.g., "2023 SCC 15") or URL path

        Returns:
            CaseData object or None if not found

        Example:
            >>> scraper = CanLIIScraper()
            >>> case = scraper.get_case_by_id("2023 SCC 15")
            >>> case = scraper.get_case_by_id("ca/scc-csc/doc/2023/2023scc15/2023scc15")
        """
        if not case_id:
            raise ValueError("Case ID is required")

        # Determine if it's a citation or URL path
        if case_id.startswith('http'):
            url = case_id
        elif '/' in case_id:
            # URL path format
            url = f"{self.base_url}/en/{case_id}.html"
        else:
            # Try to find by citation
            cases = self.search_cases(query=f'citation:"{case_id}"', limit=1)
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

    def _parse_search_result(self, result_div, language: str = 'en') -> Optional[CaseData]:
        """Parse a search result div into CaseData."""
        try:
            # Extract case name
            title_link = result_div.find('a', class_='title')
            if not title_link:
                return None

            case_name = sanitize_text(title_link.get_text())
            case_url = title_link.get('href')
            if case_url and not case_url.startswith('http'):
                case_url = f"{self.base_url}{case_url}"

            # Extract court and date
            meta_info = result_div.find('div', class_='resultmeta')
            court_name = ""
            case_date = None
            citations = []

            if meta_info:
                meta_text = sanitize_text(meta_info.get_text())

                # Extract court from meta text
                court_match = re.search(r'([^,]+),\s*(\d{4}-\d{2}-\d{2})', meta_text)
                if court_match:
                    court_name = normalize_court_name(court_match.group(1))
                    try:
                        case_date = datetime.strptime(court_match.group(2), '%Y-%m-%d')
                    except ValueError:
                        pass

                # Extract citations
                citation_matches = re.findall(r'\d{4}\s+[A-Z]+\s+\d+', meta_text)
                citations = [cite.strip() for cite in citation_matches]

            # Extract summary if available
            summary = ""
            summary_div = result_div.find('div', class_='summary')
            if summary_div:
                summary = sanitize_text(summary_div.get_text())

            # Extract case ID from URL
            case_id = ""
            if case_url:
                case_id_match = re.search(r'/([^/]+)\.html$', case_url)
                if case_id_match:
                    case_id = case_id_match.group(1)

            return CaseData(
                case_name=case_name,
                case_id=case_id,
                court=court_name,
                date=case_date,
                url=case_url,
                summary=summary,
                citations=citations,
                jurisdiction=self.jurisdiction,
                metadata={
                    'source': 'CanLII',
                    'language': language
                }
            )

        except Exception as e:
            self.logger.error(f"Error parsing search result: {str(e)}")
            return None

    def _parse_case_detail(self, soup, url: str) -> Optional[CaseData]:
        """Parse detailed case page into CaseData."""
        try:
            # Extract case name
            case_name = ""
            title_elem = soup.find('h1') or soup.find('title')
            if title_elem:
                case_name = sanitize_text(title_elem.get_text())

            # Extract court and date from header
            court_name = ""
            case_date = None
            citations = []

            # Look for court information
            court_elem = soup.find('span', class_='court')
            if court_elem:
                court_name = normalize_court_name(sanitize_text(court_elem.get_text()))

            # Look for date
            date_elem = soup.find('span', class_='date')
            if date_elem:
                date_text = sanitize_text(date_elem.get_text())
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', date_text)
                if date_match:
                    try:
                        case_date = datetime.strptime(date_match.group(1), '%Y-%m-%d')
                    except ValueError:
                        pass

            # Extract citations
            citation_elem = soup.find('span', class_='citation')
            if citation_elem:
                citation_text = sanitize_text(citation_elem.get_text())
                if citation_text:
                    citations = [citation_text]

            # Extract full text
            full_text = ""
            content_div = soup.find('div', class_='documentcontent') or soup.find('div', id='document')
            if content_div:
                # Remove navigation and other non-content elements
                for nav in content_div.find_all(['nav', 'header', 'footer']):
                    nav.decompose()
                full_text = sanitize_text(content_div.get_text())

            # Extract judges
            judges = []
            judge_pattern = r'(?:Justice|Judge|J\.)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
            judge_matches = re.findall(judge_pattern, full_text[:2000])  # Look in first part
            judges = list(set(judge_matches[:5]))  # Limit and dedupe

            # Extract case ID from URL
            case_id = ""
            case_id_match = re.search(r'/([^/]+)\.html$', url)
            if case_id_match:
                case_id = case_id_match.group(1)

            return CaseData(
                case_name=case_name,
                case_id=case_id,
                court=court_name,
                date=case_date,
                url=url,
                full_text=full_text,
                judges=judges,
                citations=citations,
                jurisdiction=self.jurisdiction,
                metadata={
                    'source': 'CanLII'
                }
            )

        except Exception as e:
            self.logger.error(f"Error parsing case detail: {str(e)}")
            return None


# Convenience functions
def get_case_by_id(case_id: str) -> Optional[CaseData]:
    """
    Get a specific case by ID from CanLII.

    Args:
        case_id: CanLII case citation or URL path

    Returns:
        CaseData object or None

    Example:
        >>> from the_junior_associate.canlii import get_case_by_id
        >>> case_text = get_case_by_id("2023 SCC 15")
        >>> if case_text:
        ...     print(case_text.case_name)
    """
    with CanLIIScraper() as scraper:
        return scraper.get_case_by_id(case_id)


def search_cases(
    query: str,
    start_date: Union[str, datetime] = None,
    end_date: Union[str, datetime] = None,
    court: str = None,
    limit: int = 100
) -> List[CaseData]:
    """
    Search for cases on CanLII.

    Args:
        query: Search query string
        start_date: Start date for search
        end_date: End date for search
        court: Court code (e.g., 'scc-csc')
        limit: Maximum number of results

    Returns:
        List of CaseData objects

    Example:
        >>> from the_junior_associate.canlii import search_cases
        >>> cases = search_cases("charter rights", court="scc-csc")
    """
    with CanLIIScraper() as scraper:
        return scraper.search_cases(
            query=query,
            start_date=start_date,
            end_date=end_date,
            court=court,
            limit=limit
        )