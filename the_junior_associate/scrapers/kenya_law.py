"""
Kenya Law scraper for The Junior Associate library.

Kenya Law provides free access to Kenyan legal documents including
court decisions, legislation, and legal notices.
"""

import re
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from urllib.parse import urlencode, quote

from ..utils.base import BaseScraper
from ..utils.data_models import CaseData
from ..utils.exceptions import ParsingError, DataNotFoundError
from ..utils.helpers import sanitize_text, validate_date, normalize_court_name


class KenyaLawScraper(BaseScraper):
    """
    Scraper for KenyaLaw.org - Kenya's legal database.

    Kenya Law provides comprehensive access to Kenyan case law from
    various courts including the Supreme Court, Court of Appeal, and High Court.
    """

    @property
    def base_url(self) -> str:
        return "https://kenyalaw.org"

    @property
    def jurisdiction(self) -> str:
        return "Kenya"

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
        Search for cases on Kenya Law.

        Args:
            query: Search query string
            start_date: Start date for search (YYYY-MM-DD)
            end_date: End date for search (YYYY-MM-DD)
            court: Court name (e.g., 'Supreme Court', 'Court of Appeal', 'High Court')
            limit: Maximum number of results (default: 100)
            **kwargs: Additional parameters like category

        Returns:
            List of CaseData objects

        Example:
            >>> scraper = KenyaLawScraper()
            >>> cases = scraper.search_cases(
            ...     query="constitutional law",
            ...     start_date="2023-01-01",
            ...     court="Supreme Court",
            ...     limit=20
            ... )
        """
        # Validate parameters
        params = self.validate_search_params(start_date, end_date, limit)

        # Build search parameters for Kenya Law
        search_params = {}

        if query:
            search_params['searchText'] = query

        if params.get('start_date'):
            search_params['startDate'] = params['start_date'].strftime('%Y-%m-%d')

        if params.get('end_date'):
            search_params['endDate'] = params['end_date'].strftime('%Y-%m-%d')

        if court:
            search_params['court'] = court

        # Category filter
        category = kwargs.get('category', 'caselaw')
        search_params['category'] = category

        # Set results limit
        search_params['limit'] = min(params.get('limit', 100), 200)

        # Make request to search page
        url = f"{self.base_url}/caselaw/search"

        try:
            response = self._make_request(url, params=search_params)
            soup = self._parse_html(response.text)
        except Exception as e:
            raise ParsingError(f"Failed to parse search results: {str(e)}")

        # Parse search results
        cases = []

        # Look for case links in search results
        case_links = soup.find_all('a', href=re.compile(r'/caselaw/cases/view/'))

        for link in case_links[:params.get('limit', 100)]:
            try:
                case_data = self._parse_search_result_link(link)
                if case_data:
                    cases.append(case_data)
            except Exception as e:
                self.logger.warning(f"Failed to parse search result: {str(e)}")
                continue

        self.logger.info(f"Found {len(cases)} cases from Kenya Law")
        return cases

    def get_case_by_id(self, case_id: str) -> Optional[CaseData]:
        """
        Retrieve a specific case by its Kenya Law ID or URL.

        Args:
            case_id: Kenya Law case ID or URL

        Returns:
            CaseData object or None if not found

        Example:
            >>> scraper = KenyaLawScraper()
            >>> case = scraper.get_case_by_id("123456")
        """
        if not case_id:
            raise ValueError("Case ID is required")

        # Determine URL format
        if case_id.startswith('http'):
            url = case_id
        elif case_id.isdigit():
            # Kenya Law case ID
            url = f"{self.base_url}/caselaw/cases/view/{case_id}"
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
            case_url = link.get('href')

            if case_url and not case_url.startswith('http'):
                case_url = f"{self.base_url}{case_url}"

            # Extract case ID from URL
            case_id = ""
            if case_url:
                case_id_match = re.search(r'/view/(\d+)', case_url)
                if case_id_match:
                    case_id = case_id_match.group(1)

            # Basic case data from search result
            return CaseData(
                case_name=case_name,
                case_id=case_id,
                url=case_url,
                jurisdiction=self.jurisdiction,
                metadata={
                    'source': 'Kenya Law'
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
                r'(Supreme Court of Kenya|Court of Appeal|High Court of Kenya)',
                r'(Environment and Land Court|Employment and Labour Relations Court)',
                r'(Magistrate\'s Court|Chief Magistrate\'s Court)'
            ]

            page_text = soup.get_text()
            for pattern in court_patterns:
                court_matches = re.findall(pattern, page_text, re.IGNORECASE)
                if court_matches:
                    court_name = normalize_court_name(court_matches[0])
                    break

            # Look for date patterns
            date_patterns = [
                r'(\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})',
                r'(\d{1,2}/\d{1,2}/\d{4})',
                r'(\d{4}-\d{2}-\d{2})'
            ]

            for pattern in date_patterns:
                date_matches = re.findall(pattern, page_text)
                if date_matches:
                    try:
                        # Try different date formats
                        date_str = date_matches[0]
                        # Remove ordinal suffixes
                        date_str = re.sub(r'(\d+)(?:st|nd|rd|th)', r'\1', date_str)

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
                r'\[(\d{4})\]\s+eKLR',
                r'(\d{4})\s+eKLR',
                r'Petition\s+No\.\s+(\d+\s+of\s+\d{4})',
                r'Civil\s+Appeal\s+No\.\s+(\d+\s+of\s+\d{4})',
                r'Criminal\s+Appeal\s+No\.\s+(\d+\s+of\s+\d{4})'
            ]

            for pattern in citation_patterns:
                citation_matches = re.findall(pattern, page_text)
                if citation_matches:
                    for match in citation_matches:
                        citations.append(match)

            # Extract full text content
            full_text = ""
            # Look for main content area
            content_selectors = [
                'div.judgment-content',
                'div.case-content',
                'div.content',
                'div#main',
                'div.main-content',
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
                r'(?:Hon\.\s+)?(?:Justice|Judge)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
                r'([A-Z][a-z]+),?\s+J\.?',
                r'Chief\s+Justice\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
                r'Deputy\s+Chief\s+Justice\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
            ]

            for pattern in judge_patterns:
                judge_matches = re.findall(pattern, full_text[:3000])  # Look in first part
                judges.extend([match.replace(' J.', '').replace(' J', '') for match in judge_matches])

            judges = list(set(judges[:5]))  # Limit and dedupe

            # Extract case ID from URL
            case_id = ""
            case_id_match = re.search(r'/view/(\d+)', url)
            if case_id_match:
                case_id = case_id_match.group(1)

            # Extract parties
            parties = []
            party_patterns = [
                r'([A-Z][a-z\s]+(?:Limited|Ltd)?)\s+[Vv]\.\s+([A-Z][a-z\s]+(?:Limited|Ltd)?)',
                r'([A-Z][a-z\s]+)\s+vs?\.\s+([A-Z][a-z\s]+)',
                r'In\s+the\s+Matter\s+of\s+([A-Z][a-z\s]+)'
            ]

            for pattern in party_patterns:
                party_matches = re.findall(pattern, case_name)
                if party_matches:
                    if isinstance(party_matches[0], tuple):
                        for match in party_matches[0]:
                            if match.strip():
                                parties.append(match.strip())
                    else:
                        parties.append(party_matches[0])
                    break

            # Extract case type
            case_type = ""
            type_patterns = [
                r'(Petition|Application|Appeal|Review)',
                r'(Civil|Criminal|Constitutional)',
                r'(Judicial Review|Habeas Corpus)'
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
                metadata={
                    'source': 'Kenya Law'
                }
            )

        except Exception as e:
            self.logger.error(f"Error parsing case detail: {str(e)}")
            return None


# Convenience functions
def get_case_by_id(case_id: str) -> Optional[CaseData]:
    """
    Get a specific case by ID from Kenya Law.

    Args:
        case_id: Kenya Law case ID

    Returns:
        CaseData object or None

    Example:
        >>> from the_junior_associate.kenya_law import get_case_by_id
        >>> case = get_case_by_id("123456")
        >>> if case:
        ...     print(case.case_name)
    """
    with KenyaLawScraper() as scraper:
        return scraper.get_case_by_id(case_id)


def search_cases(
    query: str,
    start_date: Union[str, datetime] = None,
    end_date: Union[str, datetime] = None,
    court: str = None,
    limit: int = 100
) -> List[CaseData]:
    """
    Search for cases on Kenya Law.

    Args:
        query: Search query string
        start_date: Start date for search
        end_date: End date for search
        court: Court name
        limit: Maximum number of results

    Returns:
        List of CaseData objects

    Example:
        >>> from the_junior_associate.kenya_law import search_cases
        >>> cases = search_cases("constitutional law", court="Supreme Court")
    """
    with KenyaLawScraper() as scraper:
        return scraper.search_cases(
            query=query,
            start_date=start_date,
            end_date=end_date,
            court=court,
            limit=limit
        )