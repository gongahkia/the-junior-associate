# Prompt to Claude Code

```txt
## Project Overview  
The Junior Associate is a polished and accessible Python library that aggregates a collection of lightweight scrapers targeted at various legal case law websites spanning multiple jurisdictions. Designed for legal researchers, practitioners, and developers, this library delivers easy-to-use programmatic access to scrape case judgments from key public legal databases around the world. Each scraper features simple APIs documented with code snippet examples, robust error handling, and is packaged for seamless integration into research workflows or applications.

## Supported Legal Sites  

## Installation  
```bash
pip install The Junior Associate
```

## Usage Examples  

```python
from The Junior Associate.courtlistener import fetch_recent_cases

cases = fetch_recent_cases(start_date="2023-01-01")
for case in cases:
    print(case["case_name"], case["date"], case["url"])
```

```python
from The Junior Associate.canlii import get_case_by_id

case_text = get_case_by_id("ONCA_2023_123")
print(case_text)
```

## Features  
- Lightweight, focused scrapers per jurisdiction and site.  
- Easy-to-use Python functions with consistent API design.  
- Examples provided in documentation to quickly integrate into research projects.  
- Robust scraping with retry and rate-limiting features.  
- Modular architecture easing extension or addition of new scrapers.  

## Technical Details  
- Requires Python 3.9+  
- Uses requests and BeautifulSoup4 for HTML parsing.  
- Supports JSON and XML parsing for APIs when available.  
- Clear logging and error management.  
- Packaged with setuptools for easy installation.  

## Development and Testing  
- Unit tests use pytest.  
- CI/CD pipeline ensures scraper stability against site layout changes.  

## Notes for Claude Code  
- Generate a multi-file Python package with one module per site scraper.  
- Include comprehensive README in markdown with usage and code snippets.  
- Implement main scraping logic, error handling, and example scripts for each site.  
- Provide setup.py, requirements.txt, and test suite configuration for easy packaging.  
- Document scraping target URLs and expected data extracted. 
```

# Sample Linkedin Post

```txt
Excited to announce The Junior Associate — a polished Python library offering tiny, ready-to-use scrapers for legal case law websites across multiple jurisdictions! ⚖️🐍

Whether you're a researcher, lawyer, or developer, The Junior Associate provides easy access to scrape case judgments from key public legal portals like CourtListener, AustLII, CanLII, BAILII, Singapore Judiciary, Indian Kanoon, and more.

With simple APIs and comprehensive code examples, it’s designed to accelerate legal data collection and research automation.

The library embraces modularity, robustness, and community contribution to grow as the go-to legal case scraper toolkit.

Try it out, contribute, and help empower legal research with Python!

#LegalTech #Python #WebScraping #OpenSource #LawResearch #DataScience #LegalAI #The Junior Associate
```

[![](https://img.shields.io/badge/the_junior_associate_1.0.0-passing-green)](https://github.com/gongahkia/the-junior-associate/releases/tag/1.0.0) 

# `The Junior Associate`

...

## Rationale

...

## Stack

...

## Screenshots

...

## Usage

...

## Support

> FUA reformat this into a table with the columns Source | Site | Description | Support |

- courtlistener.com — CourtListener (Free US federal and state case law database)  
- findlaw.com — FindLaw (US Supreme Court and state case law collection)  
- austlii.edu.au — Australasian Legal Information Institute (Australian Commonwealth and state courts case law) 
- canlii.org — Canadian Legal Information Institute (Canadian federal and provincial case law)  
- bailii.org — British and Irish Legal Information Institute (UK and Ireland court judgments)  
- judiciary.gov.sg — Singapore Judiciary (Official Singapore court case judgments)  
- indiankanoon.org — Indian Kanoon (Free access to Indian federal and state court judgments)  
- hklawlib.org.hk/hklii — Hong Kong Legal Information Institute (HK appellate and tribunal case law)  
- legifrance.gouv.fr — Légifrance (French Supreme and administrative court decisions)  
- germanlawarchive.iuscomp.org — German Law Archive (Selected German court judgments in English)  
- curia.europa.eu — European Court of Justice (EU law cases and judgments)  
- worldlii.org — World Legal Information Institute (Global LII case law search)  
- worldcourts.com — WorldCourts (International case law database with many jurisdictions)  
- supremecourt.gov.in — Supreme Court of India (Official Indian Supreme Court judgments)  
- kenyalaw.org — Kenya Law Online (Kenyan court case law and statutes)  
- supremecourt.japan.go.jp — Supreme Court of Japan (Japanese Supreme Court judgments in English)  
- legal-tools.org — ICC Legal Tools Database (International crimes case law database)  


## Architecture

...

## Legal

...

## Reference

... Name is in reference to the show Suits
