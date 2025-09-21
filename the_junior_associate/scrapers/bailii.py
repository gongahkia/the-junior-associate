"""
BAILII scraper for The Junior Associate library.

BAILII (British and Irish Legal Information Institute) provides free access
to British and Irish case law and legislation.
"""

import re
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from urllib.parse import urlencode, quote

from ..utils.base import BaseScraper
from ..utils.data_models import CaseData
from ..utils.exceptions import ParsingError, DataNotFoundError
from ..utils.helpers import sanitize_text, validate_date, normalize_court_name


class BAILIIScraper(BaseScraper):
    """
    Scraper for BAILII.org - British and Irish Legal Information Institute.

    BAILII provides comprehensive access to British and Irish case law from
    courts in England, Wales, Scotland, Northern Ireland, and the Republic of Ireland.
    """

    @property
    def base_url(self) -> str:
        return "https://www.bailii.org"

    @property
    def jurisdiction(self) -> str:
        return "United Kingdom"

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
        Search for cases on BAILII.

        Args:
            query: Search query string
            start_date: Start date for search (YYYY-MM-DD)
            end_date: End date for search (YYYY-MM-DD)
            court: Court abbreviation (e.g., 'UKSC', 'EWCA', 'EWHC')
            limit: Maximum number of results (default: 100)
            **kwargs: Additional parameters like jurisdiction ('uk', 'ie', 'ni', 'scot')

        Returns:
            List of CaseData objects

        Example:
            >>> scraper = BAILIIScraper()
            >>> cases = scraper.search_cases(
            ...     query="human rights",
            ...     start_date="2023-01-01",
            ...     court="UKSC",
            ...     limit=20
            ... )
        """
        # Validate parameters
        params = self.validate_search_params(start_date, end_date, limit)

        # Build search parameters for BAILII
        search_params = {
            'method': 'boolean'
        }

        if query:
            search_params['query'] = query

        if params.get('start_date'):
            search_params['date_from'] = params['start_date'].strftime('%d/%m/%Y')

        if params.get('end_date'):
            search_params['date_to'] = params['end_date'].strftime('%d/%m/%Y')

        if court:
            search_params['court'] = court

        # Jurisdiction filter
        jurisdiction = kwargs.get('jurisdiction', 'uk')
        if jurisdiction in ['uk', 'ie', 'ni', 'scot']:
            search_params['jurisdiction'] = jurisdiction

        # Set results limit
        search_params['results'] = min(params.get('limit', 100), 200)

        # Make request to search page
        url = f"{self.base_url}/cgi-bin/markup.cgi"

        try:
            response = self._make_request(url, params=search_params)
            soup = self._parse_html(response.text)
        except Exception as e:
            raise ParsingError(f"Failed to parse search results: {str(e)}")

        # Parse search results
        cases = []

        # Look for case links in search results
        case_links = soup.find_all('a', href=re.compile(r'/(uk|ie|ni|scot)/cases/'))

        for link in case_links[:params.get('limit', 100)]:
            try:
                case_data = self._parse_search_result_link(link)
                if case_data:
                    cases.append(case_data)
            except Exception as e:
                self.logger.warning(f"Failed to parse search result: {str(e)}")
                continue

        self.logger.info(f"Found {len(cases)} cases from BAILII")
        return cases

    def get_case_by_id(self, case_id: str) -> Optional[CaseData]:
        """
        Retrieve a specific case by its BAILII citation or URL path.

        Args:
            case_id: BAILII case citation or URL path

        Returns:
            CaseData object or None if not found

        Example:
            >>> scraper = BAILIIScraper()
            >>> case = scraper.get_case_by_id("uk/cases/UKSC/2023/15")
        """
        if not case_id:
            raise ValueError("Case ID is required")

        # Determine URL format
        if case_id.startswith('http'):
            url = case_id
        elif case_id.startswith(('uk/cases/', 'ie/cases/', 'ni/cases/', 'scot/cases/')):
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
                case_id_match = re.search(r'/(uk|ie|ni|scot)/cases/([^/]+/\d+/\d+)', case_url)
                if case_id_match:
                    case_id = f"{case_id_match.group(1)}/cases/{case_id_match.group(2)}"

            # Determine jurisdiction from URL
            jurisdiction = self.jurisdiction
            if '/ie/cases/' in case_url:
                jurisdiction = "Ireland"
            elif '/ni/cases/' in case_url:
                jurisdiction = "Northern Ireland"
            elif '/scot/cases/' in case_url:
                jurisdiction = "Scotland"

            # Basic case data from search result
            return CaseData(
                case_name=case_name,
                case_id=case_id,
                url=case_url,
                jurisdiction=jurisdiction,
                metadata={
                    'source': 'BAILII'
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

            # Look for court information
            court_patterns = [
                r'(Supreme Court|Court of Appeal|High Court|Crown Court|Magistrates|Employment Tribunal)',
                r'(UKSC|EWCA|EWHC|UKUT|UKFTT)',
                r'(House of Lords|Privy Council)'
            ]

            page_text = soup.get_text()
            for pattern in court_patterns:
                court_matches = re.findall(pattern, page_text, re.IGNORECASE)
                if court_matches:
                    court_name = normalize_court_name(court_matches[0])
                    break

            # Look for date patterns
            date_patterns = [
                r'(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})',
                r'(\d{4}-\d{2}-\d{2})',
                r'(\d{1,2}/\d{1,2}/\d{4})'
            ]

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
                r'\[(\d{4})\]\s+(UKSC|EWCA|EWHC|UKUT)\s+(\d+)',
                r'(\d{4})\s+(UKSC|EWCA|EWHC|UKUT)\s+(\d+)',
                r'\[(\d{4})\]\s+(\d+)\s+(WLR|All ER|AC|QB)',
                r'(\d{4})\s+(\d+)\s+(WLR|All ER|AC|QB)'
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
                r'(?:Lord|Lady|Mr|Mrs|Ms)\s+Justice\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
                r'(?:Lord|Lady)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
                r'([A-Z][a-z]+\s+LJ)',
                r'([A-Z][a-z]+\s+J\.?)'
            ]

            for pattern in judge_patterns:
                judge_matches = re.findall(pattern, full_text[:3000])  # Look in first part
                judges.extend([match.replace(' LJ', '').replace(' J.', '').replace(' J', '') for match in judge_matches])

            judges = list(set(judges[:5]))  # Limit and dedupe

            # Determine jurisdiction from URL
            jurisdiction = self.jurisdiction
            if '/ie/cases/' in url:
                jurisdiction = "Ireland"
            elif '/ni/cases/' in url:
                jurisdiction = "Northern Ireland"
            elif '/scot/cases/' in url:
                jurisdiction = "Scotland"

            # Extract case ID from URL
            case_id = ""
            case_id_match = re.search(r'/(uk|ie|ni|scot)/cases/([^/]+/\d+/\d+)', url)
            if case_id_match:
                case_id = f"{case_id_match.group(1)}/cases/{case_id_match.group(2)}"

            return CaseData(
                case_name=case_name,
                case_id=case_id,
                court=court_name,
                date=case_date,
                url=url,
                full_text=full_text,
                judges=judges,
                citations=citations,
                jurisdiction=jurisdiction,
                metadata={
                    'source': 'BAILII'
                }
            )

        except Exception as e:
            self.logger.error(f"Error parsing case detail: {str(e)}")
            return None


# Convenience functions
def get_case_by_id(case_id: str) -> Optional[CaseData]:
    """
    Get a specific case by ID from BAILII.

    Args:
        case_id: BAILII case citation or URL path

    Returns:
        CaseData object or None

    Example:
        >>> from the_junior_associate.bailii import get_case_by_id
        >>> case = get_case_by_id("uk/cases/UKSC/2023/15")
        >>> if case:
        ...     print(case.case_name)
    """
    with BAILIIScraper() as scraper:
        return scraper.get_case_by_id(case_id)


def search_cases(
    query: str,
    start_date: Union[str, datetime] = None,
    end_date: Union[str, datetime] = None,
    court: str = None,
    limit: int = 100
) -> List[CaseData]:
    """
    Search for cases on BAILII.

    Args:
        query: Search query string
        start_date: Start date for search
        end_date: End date for search
        court: Court abbreviation (e.g., 'UKSC')
        limit: Maximum number of results

    Returns:
        List of CaseData objects

    Example:
        >>> from the_junior_associate.bailii import search_cases
        >>> cases = search_cases("human rights", court="UKSC")
    """
    with BAILIIScraper() as scraper:
        return scraper.search_cases(
            query=query,
            start_date=start_date,
            end_date=end_date,
            court=court,
            limit=limit
        )