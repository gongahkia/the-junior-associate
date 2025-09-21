"""
Légifrance scraper for The Junior Associate library.

Légifrance provides free access to French legal documents including
court decisions, legislation, and regulatory texts.
"""

import re
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from urllib.parse import urlencode, quote

from ..utils.base import BaseScraper
from ..utils.data_models import CaseData
from ..utils.exceptions import ParsingError, DataNotFoundError
from ..utils.helpers import sanitize_text, validate_date, normalize_court_name


class LegifranceScraper(BaseScraper):
    """
    Scraper for Legifrance.gouv.fr - French legal database.

    Légifrance provides comprehensive access to French jurisprudence from
    the Cour de cassation, Conseil d'État, and other French courts.
    """

    @property
    def base_url(self) -> str:
        return "https://www.legifrance.gouv.fr"

    @property
    def jurisdiction(self) -> str:
        return "France"

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
        Search for cases on Légifrance.

        Args:
            query: Search query string
            start_date: Start date for search (YYYY-MM-DD)
            end_date: End date for search (YYYY-MM-DD)
            court: Court type (e.g., 'Cour de cassation', 'Conseil d État')
            limit: Maximum number of results (default: 100)
            **kwargs: Additional parameters like chamber ('civile', 'criminelle', 'sociale')

        Returns:
            List of CaseData objects

        Example:
            >>> scraper = LegifranceScraper()
            >>> cases = scraper.search_cases(
            ...     query="droit du travail",
            ...     start_date="2023-01-01",
            ...     court="Cour de cassation",
            ...     limit=20
            ... )
        """
        # Validate parameters
        params = self.validate_search_params(start_date, end_date, limit)

        # Build search parameters for Légifrance
        search_params = {
            'typePagination': 'defaut',
            'sortValue': 'SIGNATURE_DATE_DESC'
        }

        if query:
            search_params['recherche'] = query

        if params.get('start_date'):
            search_params['dateSignatureDebut'] = params['start_date'].strftime('%d/%m/%Y')

        if params.get('end_date'):
            search_params['dateSignatureFin'] = params['end_date'].strftime('%d/%m/%Y')

        if court:
            search_params['juridiction'] = court

        # Chamber filter for Court of Cassation
        chamber = kwargs.get('chamber')
        if chamber and chamber in ['civile', 'criminelle', 'sociale', 'commerciale']:
            search_params['chambre'] = chamber

        # Set results limit
        search_params['size'] = min(params.get('limit', 100), 100)  # Légifrance limit

        # Make request to search page
        url = f"{self.base_url}/search/juri"

        try:
            response = self._make_request(url, params=search_params)
            soup = self._parse_html(response.text)
        except Exception as e:
            raise ParsingError(f"Failed to parse search results: {str(e)}")

        # Parse search results
        cases = []

        # Look for decision links in search results
        decision_links = soup.find_all('a', href=re.compile(r'/juri/'))

        for link in decision_links[:params.get('limit', 100)]:
            try:
                case_data = self._parse_search_result_link(link)
                if case_data:
                    cases.append(case_data)
            except Exception as e:
                self.logger.warning(f"Failed to parse search result: {str(e)}")
                continue

        self.logger.info(f"Found {len(cases)} cases from Légifrance")
        return cases

    def get_case_by_id(self, case_id: str) -> Optional[CaseData]:
        """
        Retrieve a specific case by its Légifrance ID or URL.

        Args:
            case_id: Légifrance case ID or URL

        Returns:
            CaseData object or None if not found

        Example:
            >>> scraper = LegifranceScraper()
            >>> case = scraper.get_case_by_id("CETATEXT000047123456")
        """
        if not case_id:
            raise ValueError("Case ID is required")

        # Determine URL format
        if case_id.startswith('http'):
            url = case_id
        elif case_id.startswith('CETATEXT') or case_id.startswith('JURITEXT'):
            # Légifrance document ID format
            url = f"{self.base_url}/juri/id/{case_id}"
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
                case_id_match = re.search(r'/id/([A-Z]+\d+)', case_url)
                if case_id_match:
                    case_id = case_id_match.group(1)

            # Basic case data from search result
            return CaseData(
                case_name=case_name,
                case_id=case_id,
                url=case_url,
                jurisdiction=self.jurisdiction,
                metadata={
                    'source': 'Légifrance'
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
                r'(Cour de cassation|Conseil d\'État|Cour d\'appel|Tribunal)',
                r'(Chambre civile|Chambre criminelle|Chambre sociale|Chambre commerciale)',
                r'(CAA|TA|TGI|TI)'
            ]

            page_text = soup.get_text()
            for pattern in court_patterns:
                court_matches = re.findall(pattern, page_text, re.IGNORECASE)
                if court_matches:
                    court_name = normalize_court_name(court_matches[0])
                    break

            # Look for date patterns
            date_patterns = [
                r'(\d{1,2}\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+\d{4})',
                r'(\d{1,2}/\d{1,2}/\d{4})',
                r'(\d{4}-\d{2}-\d{2})'
            ]

            # French month mapping
            french_months = {
                'janvier': 'January', 'février': 'February', 'mars': 'March',
                'avril': 'April', 'mai': 'May', 'juin': 'June',
                'juillet': 'July', 'août': 'August', 'septembre': 'September',
                'octobre': 'October', 'novembre': 'November', 'décembre': 'December'
            }

            for pattern in date_patterns:
                date_matches = re.findall(pattern, page_text, re.IGNORECASE)
                if date_matches:
                    try:
                        # Try different date formats
                        date_str = date_matches[0]
                        if '-' in date_str:
                            case_date = datetime.strptime(date_str, '%Y-%m-%d')
                        elif '/' in date_str:
                            case_date = datetime.strptime(date_str, '%d/%m/%Y')
                        else:
                            # Convert French month to English
                            for fr_month, en_month in french_months.items():
                                if fr_month in date_str.lower():
                                    date_str = date_str.replace(fr_month, en_month)
                                    break
                            case_date = datetime.strptime(date_str, '%d %B %Y')
                        break
                    except ValueError:
                        continue

            # Extract citations and case numbers
            citation_patterns = [
                r'n°\s*(\d{2}-\d{2}\.\d{3})',
                r'Arrêt\s*n°\s*(\d+)',
                r'(\d{4})\s*Bull\.\s*civ\.\s*(\w+)',
                r'Req\.\s*n°\s*(\d{2}-\d{5})'
            ]

            for pattern in citation_patterns:
                citation_matches = re.findall(pattern, page_text)
                if citation_matches:
                    for match in citation_matches:
                        if isinstance(match, tuple):
                            citations.append(' '.join(match))
                        else:
                            citations.append(match)

            # Extract full text content
            full_text = ""
            # Look for main content area
            content_selectors = [
                'div.content',
                'div.texte-arret',
                'div#content',
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

            # Extract judges and magistrates
            judges = []
            judge_patterns = [
                r'M\.\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),?\s+président',
                r'Mme\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),?\s+président',
                r'M\.\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),?\s+conseiller',
                r'Mme\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),?\s+conseiller'
            ]

            for pattern in judge_patterns:
                judge_matches = re.findall(pattern, full_text[:3000])  # Look in first part
                judges.extend(judge_matches)

            judges = list(set(judges[:5]))  # Limit and dedupe

            # Extract case ID from URL
            case_id = ""
            case_id_match = re.search(r'/id/([A-Z]+\d+)', url)
            if case_id_match:
                case_id = case_id_match.group(1)

            # Extract parties (if civil case)
            parties = []
            # French legal party patterns
            party_patterns = [
                r'([A-Z][a-z\s]+(?:SARL|SA|SAS)?)\s+c[./]\s+([A-Z][a-z\s]+(?:SARL|SA|SAS)?)',
                r'M\.\s+([A-Z][a-z\s]+)\s+c[./]\s+([A-Z][a-z\s]+)',
                r'Mme\s+([A-Z][a-z\s]+)\s+c[./]\s+([A-Z][a-z\s]+)'
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
                metadata={
                    'source': 'Légifrance',
                    'language': 'French'
                }
            )

        except Exception as e:
            self.logger.error(f"Error parsing case detail: {str(e)}")
            return None


# Convenience functions
def get_case_by_id(case_id: str) -> Optional[CaseData]:
    """
    Get a specific case by ID from Légifrance.

    Args:
        case_id: Légifrance document ID

    Returns:
        CaseData object or None

    Example:
        >>> from the_junior_associate.legifrance import get_case_by_id
        >>> case = get_case_by_id("CETATEXT000047123456")
        >>> if case:
        ...     print(case.case_name)
    """
    with LegifranceScraper() as scraper:
        return scraper.get_case_by_id(case_id)


def search_cases(
    query: str,
    start_date: Union[str, datetime] = None,
    end_date: Union[str, datetime] = None,
    court: str = None,
    limit: int = 100
) -> List[CaseData]:
    """
    Search for cases on Légifrance.

    Args:
        query: Search query string
        start_date: Start date for search
        end_date: End date for search
        court: Court name
        limit: Maximum number of results

    Returns:
        List of CaseData objects

    Example:
        >>> from the_junior_associate.legifrance import search_cases
        >>> cases = search_cases("droit du travail", court="Cour de cassation")
    """
    with LegifranceScraper() as scraper:
        return scraper.search_cases(
            query=query,
            start_date=start_date,
            end_date=end_date,
            court=court,
            limit=limit
        )