"""
Curia Europa scraper for The Junior Associate library.

Curia provides access to European Court of Justice and General Court decisions.
"""

import re
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from urllib.parse import urlencode, quote

from ..utils.base import BaseScraper
from ..utils.data_models import CaseData
from ..utils.exceptions import ParsingError, DataNotFoundError
from ..utils.helpers import sanitize_text, validate_date, normalize_court_name


class CuriaEuropaScraper(BaseScraper):
    """
    Scraper for Curia.europa.eu - European Court of Justice database.

    Provides access to judgments and orders from the Court of Justice of the
    European Union (CJEU) and the General Court (GC).
    """

    @property
    def base_url(self) -> str:
        return "https://curia.europa.eu"

    @property
    def jurisdiction(self) -> str:
        return "European Union"

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
        Search for cases on Curia Europa.

        Args:
            query: Search query string
            start_date: Start date for search (YYYY-MM-DD)
            end_date: End date for search (YYYY-MM-DD)
            court: Court type ('CJEU', 'GC', 'CST' for Civil Service Tribunal)
            limit: Maximum number of results (default: 100)
            **kwargs: Additional parameters like language ('en', 'fr', 'de', etc.)

        Returns:
            List of CaseData objects

        Example:
            >>> scraper = CuriaEuropaScraper()
            >>> cases = scraper.search_cases(
            ...     query="fundamental rights",
            ...     start_date="2023-01-01",
            ...     court="CJEU",
            ...     limit=20
            ... )
        """
        # Validate parameters
        params = self.validate_search_params(start_date, end_date, limit)

        # Build search parameters for Curia
        search_params = {
            'page': '0',
            'size': str(min(params.get('limit', 100), 100))  # Curia limit
        }

        if query:
            search_params['text'] = query

        if params.get('start_date'):
            search_params['DD_date_start'] = params['start_date'].strftime('%d/%m/%Y')

        if params.get('end_date'):
            search_params['DD_date_end'] = params['end_date'].strftime('%d/%m/%Y')

        if court:
            # Map court names to Curia codes
            court_mapping = {
                'CJEU': 'CJ',
                'Court of Justice': 'CJ',
                'GC': 'GC',
                'General Court': 'GC',
                'CST': 'CST'
            }
            search_params['court'] = court_mapping.get(court, court)

        # Language preference
        language = kwargs.get('language', 'en')
        search_params['lang'] = language

        # Case type filter
        case_type = kwargs.get('case_type')
        if case_type:
            search_params['type'] = case_type

        # Make request to search page
        url = f"{self.base_url}/juris/liste.jsf"

        try:
            response = self._make_request(url, params=search_params)
            soup = self._parse_html(response.text)
        except Exception as e:
            raise ParsingError(f"Failed to parse search results: {str(e)}")

        # Parse search results
        cases = []

        # Look for case links in search results
        case_links = soup.find_all('a', href=re.compile(r'/juris/document/'))

        for link in case_links[:params.get('limit', 100)]:
            try:
                case_data = self._parse_search_result_link(link)
                if case_data:
                    cases.append(case_data)
            except Exception as e:
                self.logger.warning(f"Failed to parse search result: {str(e)}")
                continue

        self.logger.info(f"Found {len(cases)} cases from Curia Europa")
        return cases

    def get_case_by_id(self, case_id: str) -> Optional[CaseData]:
        """
        Retrieve a specific case by its case number or URL.

        Args:
            case_id: EU case number (e.g., "C-123/23") or document URL

        Returns:
            CaseData object or None if not found

        Example:
            >>> scraper = CuriaEuropaScraper()
            >>> case = scraper.get_case_by_id("C-123/23")
        """
        if not case_id:
            raise ValueError("Case ID is required")

        # Determine URL format
        if case_id.startswith('http'):
            url = case_id
        elif re.match(r'[CT]-\d+/\d+', case_id):
            # EU case number format
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
            case_url = link.get('href')

            if case_url and not case_url.startswith('http'):
                case_url = f"{self.base_url}{case_url}"

            # Extract case ID from case name or URL
            case_id = ""
            case_number_match = re.search(r'([CT]-\d+/\d+)', case_name)
            if case_number_match:
                case_id = case_number_match.group(1)

            # Basic case data from search result
            return CaseData(
                case_name=case_name,
                case_id=case_id,
                url=case_url,
                jurisdiction=self.jurisdiction,
                metadata={
                    'source': 'Curia Europa'
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
                r'(Court of Justice|General Court|Civil Service Tribunal)',
                r'(CJEU|CJ|GC|CST)'
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
                r'(\d{1,2}/\d{1,2}/\d{4})',
                r'(\d{4}-\d{2}-\d{2})'
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
                r'Case\s+([CT]-\d+/\d+)',
                r'Joined\s+Cases\s+([CT]-\d+/\d+\s+(?:and|to)\s+[CT]-\d+/\d+)',
                r'([CT]-\d+/\d+)',
                r'ECLI:EU:[CT]:\d{4}:\d+'
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

            # Extract judges and advocates general
            judges = []
            judge_patterns = [
                r'Judge\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
                r'President\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
                r'Advocate\s+General\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
                r'Rapporteur:\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
            ]

            for pattern in judge_patterns:
                judge_matches = re.findall(pattern, full_text[:3000])  # Look in first part
                judges.extend(judge_matches)

            judges = list(set(judges[:5]))  # Limit and dedupe

            # Extract case ID from citations or case name
            case_id = ""
            if citations:
                case_id = citations[0]
            else:
                case_number_match = re.search(r'([CT]-\d+/\d+)', case_name)
                if case_number_match:
                    case_id = case_number_match.group(1)

            # Extract parties
            parties = []
            party_patterns = [
                r'([A-Z][a-z\s]+(?:Ltd|SA|GmbH|SpA)?)\s+v\s+([A-Z][a-z\s]+(?:Ltd|SA|GmbH|SpA)?)',
                r'([A-Z][a-z\s]+)\s+v\.\s+([A-Z][a-z\s]+)'
            ]

            for pattern in party_patterns:
                party_matches = re.findall(pattern, case_name)
                if party_matches:
                    for match in party_matches[0]:
                        if match.strip():
                            parties.append(match.strip())
                    break

            # Extract legal issues/subject matter
            legal_issues = []
            subject_pattern = r'Subject-matter:\s*([^.]+)'
            subject_matches = re.findall(subject_pattern, page_text)
            if subject_matches:
                legal_issues = [issue.strip() for issue in subject_matches[:3]]

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
                jurisdiction=self.jurisdiction,
                metadata={
                    'source': 'Curia Europa'
                }
            )

        except Exception as e:
            self.logger.error(f"Error parsing case detail: {str(e)}")
            return None


# Convenience functions
def get_case_by_id(case_id: str) -> Optional[CaseData]:
    """
    Get a specific case by ID from Curia Europa.

    Args:
        case_id: EU case number

    Returns:
        CaseData object or None

    Example:
        >>> from the_junior_associate.curia_europa import get_case_by_id
        >>> case = get_case_by_id("C-123/23")
        >>> if case:
        ...     print(case.case_name)
    """
    with CuriaEuropaScraper() as scraper:
        return scraper.get_case_by_id(case_id)


def search_cases(
    query: str,
    start_date: Union[str, datetime] = None,
    end_date: Union[str, datetime] = None,
    court: str = None,
    limit: int = 100
) -> List[CaseData]:
    """
    Search for cases on Curia Europa.

    Args:
        query: Search query string
        start_date: Start date for search
        end_date: End date for search
        court: Court type ('CJEU', 'GC')
        limit: Maximum number of results

    Returns:
        List of CaseData objects

    Example:
        >>> from the_junior_associate.curia_europa import search_cases
        >>> cases = search_cases("fundamental rights", court="CJEU")
    """
    with CuriaEuropaScraper() as scraper:
        return scraper.search_cases(
            query=query,
            start_date=start_date,
            end_date=end_date,
            court=court,
            limit=limit
        )