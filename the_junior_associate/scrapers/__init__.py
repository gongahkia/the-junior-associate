"""
Legal case scrapers for The Junior Associate library.
"""

from .courtlistener import CourtListenerScraper
from .findlaw import FindLawScraper
from .austlii import AustLIIScraper
from .canlii import CanLIIScraper
from .bailii import BAILIIScraper
from .singapore_judiciary import SingaporeJudiciaryScraper
from .indian_kanoon import IndianKanoonScraper
from .hklii import HKLIIScraper
from .legifrance import LegiFranceScraper
from .german_law_archive import GermanLawArchiveScraper
from .curia_europa import CuriaEuropaScraper
from .worldlii import WorldLIIScraper
from .worldcourts import WorldCourtsScraper
from .supremecourt_india import SupremeCourtIndiaScraper
from .kenya_law import KenyaLawScraper
from .supremecourt_japan import SupremeCourtJapanScraper
from .legal_tools import LegalToolsScraper

__all__ = [
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
]