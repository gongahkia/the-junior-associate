"""
ICC Legal Tools scraper for The Junior Associate library.

ICC Legal Tools Database provides access to international criminal law documents
and decisions from various international criminal courts and tribunals.
"""

import re
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from urllib.parse import urlencode, quote

from ..utils.base import BaseScraper
from ..utils.data_models import CaseData
from ..utils.exceptions import ParsingError, DataNotFoundError
from ..utils.helpers import sanitize_text, validate_date, normalize_court_name


class LegalToolsScraper(BaseScraper):
    """
    Scraper for Legal-Tools.org - ICC Legal Tools Database.

    Provides access to decisions and documents from the International Criminal Court
    and other international criminal tribunals.
    """

    @property
    def base_url(self) -> str:
        return "https://www.legal-tools.org"

    @property
    def jurisdiction(self) -> str:
        return "International Criminal Law"

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
        Search for cases on ICC Legal Tools Database.

        Args:
            query: Search query string
            start_date: Start date for search (YYYY-MM-DD)
            end_date: End date for search (YYYY-MM-DD)
            court: Court/tribunal (e.g., 'ICC', 'ICTY', 'ICTR', 'SCSL')
            limit: Maximum number of results (default: 100)
            **kwargs: Additional parameters like document_type, language

        Returns:
            List of CaseData objects

        Example:
            >>> scraper = LegalToolsScraper()
            >>> cases = scraper.search_cases(
            ...     query="war crimes",
            ...     start_date="2023-01-01",
            ...     court="ICC",
            ...     limit=20
            ... )
        """
        # Validate parameters
        params = self.validate_search_params(start_date, end_date, limit)

        # Build search parameters for Legal Tools
        search_params = {}

        if query:
            search_params['q'] = query

        if params.get('start_date'):
            search_params['start_date'] = params['start_date'].strftime('%Y-%m-%d')

        if params.get('end_date'):
            search_params['end_date'] = params['end_date'].strftime('%Y-%m-%d')

        if court:
            search_params['court'] = court

        # Document type filter
        document_type = kwargs.get('document_type')
        if document_type:
            search_params['doc_type'] = document_type

        # Language filter
        language = kwargs.get('language')
        if language:
            search_params['lang'] = language

        # Set results limit
        search_params['limit'] = min(params.get('limit', 100), 200)

        # Make request to search page
        url = f"{self.base_url}/doc/search"

        try:
            response = self._make_request(url, params=search_params)
            soup = self._parse_html(response.text)
        except Exception as e:
            raise ParsingError(f"Failed to parse search results: {str(e)}")

        # Parse search results
        cases = []

        # Look for document links in search results
        doc_links = soup.find_all('a', href=re.compile(r'/doc/'))

        for link in doc_links[:params.get('limit', 100)]:
            try:
                case_data = self._parse_search_result_link(link)
                if case_data:
                    cases.append(case_data)
            except Exception as e:
                self.logger.warning(f"Failed to parse search result: {str(e)}")
                continue

        self.logger.info(f"Found {len(cases)} cases from ICC Legal Tools")
        return cases

    def get_case_by_id(self, case_id: str) -> Optional[CaseData]:
        """
        Retrieve a specific case by its Legal Tools ID or URL.

        Args:
            case_id: Legal Tools document ID or URL

        Returns:
            CaseData object or None if not found

        Example:
            >>> scraper = LegalToolsScraper()
            >>> case = scraper.get_case_by_id("123456")
        """
        if not case_id:
            raise ValueError("Case ID is required")

        # Determine URL format
        if case_id.startswith('http'):
            url = case_id
        elif case_id.isdigit():
            # Legal Tools document ID
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
                case_id_match = re.search(r'/doc/(\d+)/', case_url)
                if case_id_match:
                    case_id = case_id_match.group(1)

            # Determine court from case name or URL
            court_name = ""
            court_patterns = [
                (r'ICC', 'International Criminal Court'),
                (r'ICTY', 'International Criminal Tribunal for the former Yugoslavia'),
                (r'ICTR', 'International Criminal Tribunal for Rwanda'),
                (r'SCSL', 'Special Court for Sierra Leone'),
                (r'STL', 'Special Tribunal for Lebanon'),
                (r'ECCC', 'Extraordinary Chambers in the Courts of Cambodia')
            ]

            case_text = case_name.upper()
            for pattern, court in court_patterns:
                if pattern in case_text:
                    court_name = court
                    break

            # Basic case data from search result
            return CaseData(
                case_name=case_name,
                case_id=case_id,
                court=court_name,
                url=case_url,
                jurisdiction=self.jurisdiction,
                metadata={
                    'source': 'ICC Legal Tools'
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

            # Determine court from URL or case name
            court_patterns = [
                (r'ICC', 'International Criminal Court'),
                (r'ICTY', 'International Criminal Tribunal for the former Yugoslavia'),
                (r'ICTR', 'International Criminal Tribunal for Rwanda'),
                (r'SCSL', 'Special Court for Sierra Leone'),
                (r'STL', 'Special Tribunal for Lebanon'),
                (r'ECCC', 'Extraordinary Chambers in the Courts of Cambodia')
            ]

            page_text = soup.get_text()
            case_text = case_name.upper()

            for pattern, court in court_patterns:
                if pattern in case_text or pattern in page_text.upper():
                    court_name = court
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

            # Extract case numbers and citations
            citation_patterns = [
                r'Case\s+No\.\s+([A-Z]+-\d+)',
                r'IT-\d+-\d+',
                r'ICTR-\d+-\d+',
                r'SCSL-\d+-\d+',
                r'STL-\d+-\d+',
                r'(\d{3}-\d{2}-\d{6})'  # ECCC format
            ]

            for pattern in citation_patterns:
                citation_matches = re.findall(pattern, page_text)
                if citation_matches:
                    citations.extend(citation_matches)

            # Extract full text content
            full_text = ""
            # Look for main content area
            content_selectors = [
                'div.document-content',
                'div.judgment-content',
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
                r'(?:Judge|Justice)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
                r'Presiding\s+Judge\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
                r'([A-Z][a-z]+),?\s+(?:Judge|Justice)'
            ]

            for pattern in judge_patterns:
                judge_matches = re.findall(pattern, full_text[:3000])  # Look in first part
                judges.extend(judge_matches)

            judges = list(set(judges[:5]))  # Limit and dedupe

            # Extract case ID from URL
            case_id = ""
            case_id_match = re.search(r'/doc/(\d+)/', url)
            if case_id_match:
                case_id = case_id_match.group(1)

            # Extract parties (accused/prosecution)
            parties = []
            party_patterns = [
                r'Prosecutor\s+v\.?\s+([A-Z][a-z\s]+)',
                r'Case\s+against\s+([A-Z][a-z\s]+)',
                r'([A-Z][a-z\s]+)\s+Case'
            ]

            for pattern in party_patterns:
                party_matches = re.findall(pattern, case_name)
                if party_matches:
                    parties.extend(party_matches)
                    break

            # Extract case type/document type
            case_type = ""
            type_patterns = [
                r'(Judgment|Decision|Order|Warrant)',
                r'(Trial|Appeal|Preliminary|Interlocutory)',
                r'(Indictment|Sentencing|Acquittal|Conviction)'
            ]

            for pattern in type_patterns:
                type_matches = re.findall(pattern, case_name, re.IGNORECASE)
                if type_matches:
                    case_type = type_matches[0]
                    break

            # Extract legal issues (crimes charged)
            legal_issues = []
            crime_patterns = [
                r'(War crimes|Crimes against humanity|Genocide)',
                r'(Article \d+[a-z]?)',
                r'(Grave breaches|Violations of the laws)',
                r'(Murder|Torture|Persecution|Deportation)'
            ]

            for pattern in crime_patterns:
                crime_matches = re.findall(pattern, full_text[:2000], re.IGNORECASE)
                legal_issues.extend(crime_matches[:3])  # Limit to first 3

            legal_issues = list(set(legal_issues))

            return CaseData(
                case_name=case_name,
                case_id=case_id,
                court=court_name,
                date=case_date,
                url=url,
                full_text=full_text,
                judges=judges,
                parties=parties,
                legal_issues=legal_issues,
                citations=citations,
                case_type=case_type,
                jurisdiction=self.jurisdiction,
                metadata={
                    'source': 'ICC Legal Tools'
                }
            )

        except Exception as e:
            self.logger.error(f"Error parsing case detail: {str(e)}")
            return None


# Convenience functions
def get_case_by_id(case_id: str) -> Optional[CaseData]:
    """
    Get a specific case by ID from ICC Legal Tools.

    Args:
        case_id: Legal Tools document ID

    Returns:
        CaseData object or None

    Example:
        >>> from the_junior_associate.legal_tools import get_case_by_id
        >>> case = get_case_by_id("123456")
        >>> if case:
        ...     print(case.case_name)
    """
    with LegalToolsScraper() as scraper:
        return scraper.get_case_by_id(case_id)


def search_cases(
    query: str,
    start_date: Union[str, datetime] = None,
    end_date: Union[str, datetime] = None,
    court: str = None,
    limit: int = 100
) -> List[CaseData]:
    """
    Search for cases on ICC Legal Tools Database.

    Args:
        query: Search query string
        start_date: Start date for search
        end_date: End date for search
        court: Court/tribunal abbreviation
        limit: Maximum number of results

    Returns:
        List of CaseData objects

    Example:
        >>> from the_junior_associate.legal_tools import search_cases
        >>> cases = search_cases("war crimes", court="ICC")
    """
    with LegalToolsScraper() as scraper:
        return scraper.search_cases(
            query=query,
            start_date=start_date,
            end_date=end_date,
            court=court,
            limit=limit
        )