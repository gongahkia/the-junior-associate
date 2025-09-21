"""
AustLII scraper for The Junior Associate library.

AustLII (Australasian Legal Information Institute) provides free access
to Australian and New Zealand case law and legislation.
"""

import re
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from urllib.parse import urlencode, quote

from ..utils.base import BaseScraper
from ..utils.data_models import CaseData
from ..utils.exceptions import ParsingError, DataNotFoundError
from ..utils.helpers import sanitize_text, validate_date, normalize_court_name


class AustLIIScraper(BaseScraper):
    """
    Scraper for AustLII.edu.au - Australasian Legal Information Institute.

    AustLII provides comprehensive access to Australian and New Zealand
    case law from federal, state, and territorial courts and tribunals.
    """

    @property
    def base_url(self) -> str:
        return "https://www.austlii.edu.au"

    @property
    def jurisdiction(self) -> str:
        return "Australia"

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
        Search for cases on AustLII.

        Args:
            query: Search query string
            start_date: Start date for search (YYYY-MM-DD)
            end_date: End date for search (YYYY-MM-DD)
            court: Court abbreviation (e.g., 'HCA', 'NSWCA')
            limit: Maximum number of results (default: 100)
            **kwargs: Additional parameters

        Returns:
            List of CaseData objects

        Example:
            >>> scraper = AustLIIScraper()
            >>> cases = scraper.search_cases(
            ...     query="constitutional law",
            ...     start_date="2023-01-01",
            ...     court="HCA",
            ...     limit=20
            ... )
        """
        # Validate parameters
        params = self.validate_search_params(start_date, end_date, limit)

        # Build search parameters for AustLII
        search_params = {}

        if query:
            search_params['query'] = query

        if params.get('start_date'):
            search_params['dfrom'] = params['start_date'].strftime('%d/%m/%Y')

        if params.get('end_date'):
            search_params['dto'] = params['end_date'].strftime('%d/%m/%Y')

        if court:
            search_params['court'] = court

        # Set results limit
        search_params['results'] = min(params.get('limit', 100), 200)

        # Make request to search page
        url = f"{self.base_url}/cgi-bin/sinodisp/au/cases/cth/HCA/"

        try:
            response = self._make_request(url, params=search_params)
            soup = self._parse_html(response.text)
        except Exception as e:
            raise ParsingError(f"Failed to parse search results: {str(e)}")

        # Parse search results
        cases = []

        # Look for case links in search results
        case_links = soup.find_all('a', href=re.compile(r'/au/cases/'))

        for link in case_links[:params.get('limit', 100)]:
            try:
                case_data = self._parse_search_result_link(link)
                if case_data:
                    cases.append(case_data)
            except Exception as e:
                self.logger.warning(f"Failed to parse search result: {str(e)}")
                continue

        self.logger.info(f"Found {len(cases)} cases from AustLII")
        return cases

    def get_case_by_id(self, case_id: str) -> Optional[CaseData]:
        """
        Retrieve a specific case by its AustLII citation or URL path.

        Args:
            case_id: AustLII case citation or URL path

        Returns:
            CaseData object or None if not found

        Example:
            >>> scraper = AustLIIScraper()
            >>> case = scraper.get_case_by_id("au/cases/cth/HCA/2023/15")
        """
        if not case_id:
            raise ValueError("Case ID is required")

        # Determine URL format
        if case_id.startswith('http'):
            url = case_id
        elif case_id.startswith('au/cases/'):
            url = f"{self.base_url}/{case_id}.html"
        else:
            # Try searching for the citation
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
            case_url = link.get('href')

            if case_url and not case_url.startswith('http'):
                case_url = f"{self.base_url}{case_url}"

            # Extract case ID from URL
            case_id = ""
            if case_url:
                case_id_match = re.search(r'/au/cases/([^/]+/[^/]+/[^/]+/\d+/\d+)', case_url)
                if case_id_match:
                    case_id = case_id_match.group(1)

            # Basic case data from search result
            return CaseData(
                case_name=case_name,
                case_id=case_id,
                url=case_url,
                jurisdiction=self.jurisdiction,
                metadata={
                    'source': 'AustLII'
                }
            )

        except Exception as e:
            self.logger.error(f"Error parsing search result link: {str(e)}")
            return None

    def _parse_case_detail(self, soup, url: str) -> Optional[CaseData]:
        """Parse detailed case page into CaseData."""
        try:
            # Extract case name from title or heading
            case_name = ""
            title_elem = soup.find('title')
            if title_elem:
                case_name = sanitize_text(title_elem.get_text())

            # Try h1 if title doesn't work
            if not case_name:
                h1_elem = soup.find('h1')
                if h1_elem:
                    case_name = sanitize_text(h1_elem.get_text())

            # Extract court and date information
            court_name = ""
            case_date = None
            citations = []

            # Look for court information in the page
            court_pattern = r'(High Court of Australia|Federal Court of Australia|NSW Court of Appeal|Victorian Court of Appeal)'
            court_matches = re.findall(court_pattern, soup.get_text())
            if court_matches:
                court_name = normalize_court_name(court_matches[0])

            # Look for date patterns
            date_patterns = [
                r'(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})',
                r'(\d{4}-\d{2}-\d{2})',
                r'(\d{1,2}/\d{1,2}/\d{4})'
            ]

            page_text = soup.get_text()
            for pattern in date_patterns:
                date_matches = re.findall(pattern, page_text)
                if date_matches:
                    try:
                        # Try different date formats
                        date_str = date_matches[0]
                        if '-' in date_str:
                            case_date = datetime.strptime(date_str, '%Y-%m-%d')
                        elif '/' in date_str:
                            case_date = datetime.strptime(date_str, '%d/%m/%Y')
                        else:
                            case_date = datetime.strptime(date_str, '%d %B %Y')
                        break
                    except ValueError:
                        continue

            # Extract citations
            citation_patterns = [
                r'\[(\d{4})\]\s+HCA\s+(\d+)',
                r'(\d{4})\s+HCA\s+(\d+)',
                r'\[(\d{4})\]\s+[A-Z]+\s+(\d+)'
            ]

            for pattern in citation_patterns:
                citation_matches = re.findall(pattern, page_text)
                if citation_matches:
                    for match in citation_matches:
                        if len(match) == 2:
                            citations.append(f"[{match[0]}] HCA {match[1]}")

            # Extract full text content
            full_text = ""
            # Look for main content area
            content_selectors = [
                'div.judgment',
                'div.content',
                'div#main',
                'body'
            ]

            for selector in content_selectors:
                content_div = soup.select_one(selector)
                if content_div:
                    # Remove navigation and other non-content elements
                    for unwanted in content_div.find_all(['nav', 'header', 'footer', 'script', 'style']):
                        unwanted.decompose()
                    full_text = sanitize_text(content_div.get_text())
                    break

            # Extract judges
            judges = []
            judge_patterns = [
                r'(?:Justice|J\.)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
                r'([A-Z][a-z]+\s+J\.?)'
            ]

            for pattern in judge_patterns:
                judge_matches = re.findall(pattern, full_text[:3000])  # Look in first part
                judges.extend([match.replace(' J.', '').replace(' J', '') for match in judge_matches])

            judges = list(set(judges[:5]))  # Limit and dedupe

            # Extract case ID from URL
            case_id = ""
            case_id_match = re.search(r'/au/cases/([^/]+/[^/]+/[^/]+/\d+/\d+)', url)
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
                    'source': 'AustLII'
                }
            )

        except Exception as e:
            self.logger.error(f"Error parsing case detail: {str(e)}")
            return None


# Convenience functions
def get_case_by_id(case_id: str) -> Optional[CaseData]:
    """
    Get a specific case by ID from AustLII.

    Args:
        case_id: AustLII case citation or URL path

    Returns:
        CaseData object or None

    Example:
        >>> from the_junior_associate.austlii import get_case_by_id
        >>> case = get_case_by_id("au/cases/cth/HCA/2023/15")
        >>> if case:
        ...     print(case.case_name)
    """
    with AustLIIScraper() as scraper:
        return scraper.get_case_by_id(case_id)


def search_cases(
    query: str,
    start_date: Union[str, datetime] = None,
    end_date: Union[str, datetime] = None,
    court: str = None,
    limit: int = 100
) -> List[CaseData]:
    """
    Search for cases on AustLII.

    Args:
        query: Search query string
        start_date: Start date for search
        end_date: End date for search
        court: Court abbreviation (e.g., 'HCA')
        limit: Maximum number of results

    Returns:
        List of CaseData objects

    Example:
        >>> from the_junior_associate.austlii import search_cases
        >>> cases = search_cases("constitutional law", court="HCA")
    """
    with AustLIIScraper() as scraper:
        return scraper.search_cases(
            query=query,
            start_date=start_date,
            end_date=end_date,
            court=court,
            limit=limit
        )