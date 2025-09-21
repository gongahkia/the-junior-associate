"""
The Junior Associate - A polished Python library for scraping legal case law
from multiple jurisdictions.

Author: The Junior Associate Contributors
License: MIT
"""

__version__ = "1.0.0"
__author__ = "The Junior Associate Contributors"
__email__ = "contributors@thejuniorassociate.org"
__description__ = "A polished Python library for scraping legal case law from multiple jurisdictions"

from .scrapers import (
    CourtListenerScraper,
    FindLawScraper,
    AustLIIScraper,
    CanLIIScraper,
    BAILIIScraper,
    SingaporeJudiciaryScraper,
    IndianKanoonScraper,
    HKLIIScraper,
    LegiFranceScraper,
    GermanLawArchiveScraper,
    CuriaEuropaScraper,
    WorldLIIScraper,
    WorldCourtsScraper,
    SupremeCourtIndiaScraper,
    KenyaLawScraper,
    SupremeCourtJapanScraper,
    LegalToolsScraper,
)

from .utils import (
    CaseData,
    ScrapingError,
    RateLimitError,
    ParsingError,
    NetworkError,
    validate_date,
    sanitize_text,
    setup_logger,
)

__all__ = [
    # Scrapers
    "CourtListenerScraper",
    "FindLawScraper",
    "AustLIIScraper",
    "CanLIIScraper",
    "BAILIIScraper",
    "SingaporeJudiciaryScraper",
    "IndianKanoonScraper",
    "HKLIIScraper",
    "LegiFranceScraper",
    "GermanLawArchiveScraper",
    "CuriaEuropaScraper",
    "WorldLIIScraper",
    "WorldCourtsScraper",
    "SupremeCourtIndiaScraper",
    "KenyaLawScraper",
    "SupremeCourtJapanScraper",
    "LegalToolsScraper",
    # Utilities
    "CaseData",
    "ScrapingError",
    "RateLimitError",
    "ParsingError",
    "NetworkError",
    "validate_date",
    "sanitize_text",
    "setup_logger",
]