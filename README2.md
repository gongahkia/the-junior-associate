# The Junior Associate

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**The Junior Associate** is a polished and comprehensive Python library that provides easy-to-use scrapers for legal case law from multiple jurisdictions worldwide. Designed for legal researchers, practitioners, and developers, this library delivers programmatic access to scrape case judgments from key public legal databases around the globe.

> *"In reference to the show Suits"* - Because every legal researcher needs a reliable associate.

## 🚀 Features

### Core Capabilities
- **17 Legal Scrapers** covering major jurisdictions (US, Canada, Australia, UK, EU, Asia, etc.)
- **Unified API** with consistent interface across all scrapers
- **Robust Error Handling** with retry logic and rate limiting
- **Rich Data Models** with structured case information
- **Command Line Interface** for quick searches and automation
- **Type Safety** with comprehensive type hints
- **Professional Logging** with configurable verbosity levels

### Supported Legal Databases

| Database | Jurisdiction | Coverage | Status |
|----------|-------------|----------|---------|
| **CourtListener** | United States | Federal & State Courts | ✅ Active |
| **FindLaw** | United States | Supreme Court & State Law | ✅ Active |
| **AustLII** | Australia/New Zealand | Commonwealth & State Courts | ✅ Active |
| **CanLII** | Canada | Federal & Provincial Courts | ✅ Active |
| **BAILII** | UK & Ireland | All UK & Irish Courts | ✅ Active |
| **Singapore Judiciary** | Singapore | Official Court Judgments | ✅ Active |
| **Indian Kanoon** | India | Federal & State Courts | ✅ Active |
| **HKLII** | Hong Kong | Appellate & Tribunal Cases | ✅ Active |
| **Légifrance** | France | Supreme & Administrative Courts | ✅ Active |
| **German Law Archive** | Germany | Selected Federal Court Cases | ✅ Active |
| **Curia Europa** | European Union | ECJ & General Court | ✅ Active |
| **WorldLII** | International | Global Legal Databases | ✅ Active |
| **WorldCourts** | International | International Court Cases | ✅ Active |
| **Supreme Court of India** | India | Official Supreme Court | ✅ Active |
| **Kenya Law** | Kenya | Kenyan Court Cases | ✅ Active |
| **Supreme Court of Japan** | Japan | Japanese Supreme Court | ✅ Active |
| **ICC Legal Tools** | International | International Criminal Law | ✅ Active |

## 📦 Installation

### Requirements
- Python 3.9 or higher
- Internet connection for scraping

### From PyPI (Recommended)
```bash
pip install the-junior-associate
```

### From Source
```bash
git clone https://github.com/gongahkia/the-junior-associate.git
cd the-junior-associate
pip install -e .
```

### Development Installation
```bash
git clone https://github.com/gongahkia/the-junior-associate.git
cd the-junior-associate
pip install -e ".[dev]"
```

## 🔧 Quick Start

### Basic Python Usage

```python
from the_junior_associate import CourtListenerScraper, CaseData

# Search for cases
with CourtListenerScraper() as scraper:
    cases = scraper.search_cases(
        query="privacy rights",
        start_date="2023-01-01",
        limit=10
    )

    for case in cases:
        print(f"{case.case_name} - {case.date}")
        print(f"Court: {case.court}")
        print(f"URL: {case.url}")
        print("-" * 50)
```

### Command Line Usage

```bash
# List available scrapers
junior-associate list-scrapers

# Search for cases
junior-associate search courtlistener "constitutional law" --limit 5

# Search with date range
junior-associate search canlii "charter rights" \
    --start-date 2023-01-01 \
    --end-date 2023-12-31 \
    --limit 10

# Get specific case
junior-associate get-case courtlistener "12345"

# Output to JSON file
junior-associate search bailii "human rights" \
    --format json \
    --output results.json
```

## 📖 Comprehensive Usage Guide

### 1. Scraper Classes

Each jurisdiction has its own scraper class with consistent methods:

```python
from the_junior_associate import (
    CourtListenerScraper,    # US Federal & State
    CanLIIScraper,           # Canadian Courts
    AustLIIScraper,          # Australian Courts
    BAILIIScraper,           # UK & Ireland
    CuriaEuropaScraper,      # EU Courts
    # ... and 12 more
)
```

### 2. Search Parameters

All scrapers support these common parameters:

```python
scraper.search_cases(
    query="search terms",           # Search query
    start_date="2023-01-01",       # Start date (YYYY-MM-DD)
    end_date="2023-12-31",         # End date (YYYY-MM-DD)
    court="Supreme Court",         # Court filter
    limit=100,                     # Maximum results
    **kwargs                       # Scraper-specific options
)
```

### 3. Case Data Structure

All scrapers return `CaseData` objects with consistent fields:

```python
@dataclass
class CaseData:
    case_name: str                    # Name of the case
    case_id: Optional[str] = None     # Unique case identifier
    court: Optional[str] = None       # Court name
    date: Optional[datetime] = None   # Decision date
    url: Optional[str] = None         # Original URL
    summary: Optional[str] = None     # Case summary
    full_text: Optional[str] = None   # Full case text
    judges: List[str] = field(default_factory=list)      # Judge names
    parties: List[str] = field(default_factory=list)     # Party names
    citations: List[str] = field(default_factory=list)   # Legal citations
    legal_issues: List[str] = field(default_factory=list) # Legal topics
    case_type: Optional[str] = None   # Type of case
    jurisdiction: Optional[str] = None # Jurisdiction
    metadata: Dict[str, Any] = field(default_factory=dict) # Additional data
```

### 4. Advanced Examples

#### Multi-Jurisdiction Search
```python
from the_junior_associate import CourtListenerScraper, CanLIIScraper, BAILIIScraper

scrapers = [
    ("US", CourtListenerScraper()),
    ("Canada", CanLIIScraper()),
    ("UK", BAILIIScraper())
]

all_cases = []
query = "data protection"

for jurisdiction, scraper in scrapers:
    with scraper:
        cases = scraper.search_cases(query=query, limit=5)
        for case in cases:
            case.metadata["search_jurisdiction"] = jurisdiction
            all_cases.append(case)

print(f"Found {len(all_cases)} cases across jurisdictions")
```

#### Case Analysis with Full Text
```python
from the_junior_associate import IndianKanoonScraper

with IndianKanoonScraper() as scraper:
    cases = scraper.search_cases(
        query="fundamental rights",
        start_date="2020-01-01",
        limit=10
    )

    for case in cases:
        # Get full case details
        detailed_case = scraper.get_case_by_id(case.case_id)

        if detailed_case and detailed_case.full_text:
            # Analyze case text
            word_count = len(detailed_case.full_text.split())
            print(f"{detailed_case.case_name}")
            print(f"Word count: {word_count}")
            print(f"Judges: {', '.join(detailed_case.judges)}")
            print(f"Legal issues: {', '.join(detailed_case.legal_issues)}")
```

#### Batch Processing with Error Handling
```python
import logging
from the_junior_associate import CourtListenerScraper, setup_logger

# Set up logging
logger = setup_logger("batch_processor", logging.INFO)

case_ids = ["12345", "67890", "11111"]

with CourtListenerScraper() as scraper:
    successful_cases = []
    failed_ids = []

    for case_id in case_ids:
        try:
            case = scraper.get_case_by_id(case_id)
            if case:
                successful_cases.append(case)
                logger.info(f"Successfully retrieved case {case_id}")
            else:
                failed_ids.append(case_id)
                logger.warning(f"Case {case_id} not found")
        except Exception as e:
            failed_ids.append(case_id)
            logger.error(f"Error retrieving case {case_id}: {e}")

    print(f"Successfully retrieved: {len(successful_cases)} cases")
    print(f"Failed: {len(failed_ids)} cases")
```

### 5. Jurisdiction-Specific Features

#### US Courts (CourtListener)
```python
with CourtListenerScraper() as scraper:
    cases = scraper.search_cases(
        query="privacy",
        court="scotus",  # Supreme Court
        judge="Roberts",
        case_name="United States",
        limit=20
    )
```

#### Canadian Courts (CanLII)
```python
with CanLIIScraper() as scraper:
    cases = scraper.search_cases(
        query="charter rights",
        court="scc-csc",  # Supreme Court of Canada
        language="en",     # English or French
        limit=15
    )
```

#### EU Courts (Curia Europa)
```python
with CuriaEuropaScraper() as scraper:
    cases = scraper.search_cases(
        query="fundamental rights",
        court="CJEU",      # Court of Justice
        case_type="preliminary",
        language="en",
        limit=10
    )
```

## 🛠️ Command Line Interface (CLI)

The Junior Associate includes a powerful CLI for quick access and automation.

### Available Commands

```bash
# List all available scrapers
junior-associate list-scrapers

# Search for cases
junior-associate search <scraper> <query> [options]

# Get specific case by ID
junior-associate get-case <scraper> <case_id> [options]
```

### CLI Options

#### Search Command
```bash
junior-associate search courtlistener "constitutional law" \
    --start-date 2023-01-01 \
    --end-date 2023-12-31 \
    --court "Supreme Court" \
    --limit 50 \
    --format json \
    --output results.json \
    --verbose
```

#### Get Case Command
```bash
junior-associate get-case canlii "2023 SCC 15" \
    --format text \
    --output case_details.txt
```

### Output Formats

#### Text Format (Default)
```
Case: Miranda v. Arizona
ID: 384-US-436
Court: Supreme Court of the United States
Date: 1966-06-13
URL: https://example.com/cases/miranda-v-arizona
Jurisdiction: United States
Citations: 384 U.S. 436, 86 S. Ct. 1602
Judges: Warren, Black, Douglas, Clark, Harlan, Brennan, Stewart, White, Fortas
Parties: Miranda, Arizona
Summary: The Court held that both inculpatory and exculpatory statements...
```

#### JSON Format
```json
{
  "case_name": "Miranda v. Arizona",
  "case_id": "384-US-436",
  "court": "Supreme Court of the United States",
  "date": "1966-06-13T00:00:00",
  "url": "https://example.com/cases/miranda-v-arizona",
  "summary": "The Court held that both inculpatory and exculpatory statements...",
  "jurisdiction": "United States",
  "citations": ["384 U.S. 436", "86 S. Ct. 1602"],
  "judges": ["Warren", "Black", "Douglas"],
  "parties": ["Miranda", "Arizona"],
  "legal_issues": ["Constitutional Law", "Criminal Procedure"],
  "case_type": "Criminal",
  "metadata": {
    "source": "CourtListener",
    "scraped_at": "2023-12-01T10:30:00Z"
  }
}
```

#### CSV Format
```csv
"Miranda v. Arizona","384-US-436","Supreme Court of the United States","1966-06-13","https://example.com/cases/miranda-v-arizona","United States"
```

## 🔒 Rate Limiting & Ethics

### Built-in Rate Limiting
- Automatic delays between requests (configurable)
- Respect for robots.txt files
- HTTP 429 response handling with exponential backoff
- Request throttling per jurisdiction

### Ethical Scraping Practices
```python
# Configure rate limiting
with CourtListenerScraper() as scraper:
    scraper.rate_limit_delay = 2.0  # 2 seconds between requests
    scraper.respect_robots_txt = True
    scraper.max_retries = 3

    cases = scraper.search_cases(query="test", limit=10)
```

### Best Practices
1. **Start Small**: Test with small limits before large-scale scraping
2. **Use Caching**: Avoid duplicate requests for the same data
3. **Monitor Performance**: Check website response times
4. **Be Respectful**: Follow terms of service and robots.txt
5. **Handle Errors**: Implement proper error handling and logging

## 🧪 Testing

### Running Tests
```bash
# Install test dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run with coverage
pytest --cov=the_junior_associate --cov-report=html

# Run specific test file
pytest tests/test_scrapers/test_base_scraper.py

# Run with verbose output
pytest -v
```

### Test Structure
```
tests/
├── conftest.py              # Pytest fixtures
├── test_utils/
│   ├── test_helpers.py      # Utility function tests
│   ├── test_data_models.py  # Data model tests
│   └── test_exceptions.py   # Exception handling tests
├── test_scrapers/
│   ├── test_base_scraper.py # Base scraper tests
│   ├── test_courtlistener.py
│   ├── test_canlii.py
│   └── ...                  # Individual scraper tests
└── integration/
    ├── test_live_scraping.py # Live API tests (rate limited)
    └── test_cli.py          # CLI integration tests
```

### Mock Testing
The library includes comprehensive mocking for offline testing:

```python
import pytest
from unittest.mock import Mock
from the_junior_associate import CourtListenerScraper

def test_search_with_mock(mock_response):
    """Test scraper with mocked HTTP response."""
    with CourtListenerScraper() as scraper:
        # Mock the _make_request method
        scraper._make_request = Mock(return_value=mock_response)

        cases = scraper.search_cases(query="test", limit=1)
        assert len(cases) > 0
```

## 🏗️ Architecture

### Package Structure
```
the_junior_associate/
├── __init__.py              # Main package exports
├── cli.py                   # Command line interface
├── scrapers/
│   ├── __init__.py          # Scraper exports
│   ├── courtlistener.py     # US federal & state courts
│   ├── findlaw.py           # US Supreme Court
│   ├── canlii.py            # Canadian courts
│   ├── austlii.py           # Australian courts
│   ├── bailii.py            # UK & Ireland courts
│   ├── singapore_judiciary.py
│   ├── indian_kanoon.py
│   ├── hklii.py             # Hong Kong courts
│   ├── legifrance.py        # French courts
│   ├── german_law_archive.py
│   ├── curia_europa.py      # EU courts
│   ├── worldlii.py          # International courts
│   ├── worldcourts.py       # International courts
│   ├── supremecourt_india.py
│   ├── kenya_law.py
│   ├── supremecourt_japan.py
│   └── legal_tools.py       # ICC Legal Tools
└── utils/
    ├── __init__.py          # Utility exports
    ├── base.py              # Base scraper class
    ├── data_models.py       # Data structures
    ├── exceptions.py        # Custom exceptions
    └── helpers.py           # Helper functions
```

### Base Scraper Architecture
All scrapers inherit from `BaseScraper` which provides:
- Session management with automatic retries
- Rate limiting and request throttling
- HTML parsing with BeautifulSoup
- Consistent error handling
- Logging integration

```python
class BaseScraper(ABC):
    """Abstract base class for all legal case scrapers."""

    @property
    @abstractmethod
    def base_url(self) -> str:
        """Base URL for the legal database."""
        pass

    @property
    @abstractmethod
    def jurisdiction(self) -> str:
        """Legal jurisdiction covered by this scraper."""
        pass

    @abstractmethod
    def search_cases(self, **kwargs) -> List[CaseData]:
        """Search for cases based on criteria."""
        pass

    def get_case_by_id(self, case_id: str) -> Optional[CaseData]:
        """Retrieve specific case by ID."""
        pass
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup
```bash
# Clone the repository
git clone https://github.com/gongahkia/the-junior-associate.git
cd the-junior-associate

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Run pre-commit hooks
pre-commit install
```

### Code Quality Standards
- **Black**: Code formatting
- **MyPy**: Type checking
- **Flake8**: Linting
- **Pytest**: Testing with >90% coverage
- **Pre-commit**: Automated quality checks

### Adding New Scrapers
1. Create new scraper class inheriting from `BaseScraper`
2. Implement required abstract methods
3. Add comprehensive tests
4. Update documentation
5. Submit pull request

## 📋 Changelog

### Version 1.0.0 (2023-12-01)
- ✨ Initial release with 17 legal scrapers
- 🎯 Unified API across all scrapers
- 🖥️ Command line interface
- 📊 Comprehensive data models
- 🧪 Full test suite with >90% coverage
- 📚 Complete documentation and examples

## 🔗 Related Projects

- **Legal Citation Parser**: Parse and normalize legal citations
- **Case Law Analyzer**: Natural language processing for legal texts
- **Legal Research Assistant**: AI-powered legal research tools

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚖️ Legal Disclaimer

This library is designed for legitimate legal research and educational purposes. Users must:

1. **Respect Terms of Service**: Each legal database has its own terms of service
2. **Follow Rate Limits**: Do not overwhelm servers with excessive requests
3. **Check Copyright**: Some case law may be subject to copyright restrictions
4. **Verify Accuracy**: Always verify information from original sources
5. **Professional Use**: This tool supplements but does not replace professional legal advice

The authors are not responsible for any misuse of this library or any legal consequences arising from its use.

## 🙏 Acknowledgments

- Thanks to all the legal databases that provide public access to case law
- Inspired by the legal research community's need for better tools
- Built with ❤️ for lawyers, researchers, and developers

## 📞 Support

- **Documentation**: [https://the-junior-associate.readthedocs.io/](https://the-junior-associate.readthedocs.io/)
- **Issues**: [GitHub Issues](https://github.com/gongahkia/the-junior-associate/issues)
- **Discussions**: [GitHub Discussions](https://github.com/gongahkia/the-junior-associate/discussions)
- **Email**: contributors@thejuniorassociate.org

---

*The Junior Associate - Your reliable partner in legal research* ⚖️