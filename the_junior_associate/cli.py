"""
Command-line interface for The Junior Associate library.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from . import (
    CourtListenerScraper,
    FindLawScraper,
    AustLIIScraper,
    CanLIIScraper,
    BAILIIScraper,
    SingaporeJudiciaryScraper,
    IndianKanoonScraper,
    HKLIIScraper,
    LegifranceScraper,
    GermanLawArchiveScraper,
    CuriaEuropaScraper,
    WorldLIIScraper,
    WorldCourtsScraper,
    SupremeCourtIndiaScraper,
    KenyaLawScraper,
    SupremeCourtJapanScraper,
    LegalToolsScraper,
    CaseData,
    setup_logger,
)

# Available scrapers mapping
SCRAPERS = {
    "courtlistener": CourtListenerScraper,
    "findlaw": FindLawScraper,
    "austlii": AustLIIScraper,
    "canlii": CanLIIScraper,
    "bailii": BAILIIScraper,
    "singapore": SingaporeJudiciaryScraper,
    "indian-kanoon": IndianKanoonScraper,
    "hklii": HKLIIScraper,
    "legifrance": LegifranceScraper,
    "german-law": GermanLawArchiveScraper,
    "curia-europa": CuriaEuropaScraper,
    "worldlii": WorldLIIScraper,
    "worldcourts": WorldCourtsScraper,
    "supremecourt-india": SupremeCourtIndiaScraper,
    "kenya-law": KenyaLawScraper,
    "supremecourt-japan": SupremeCourtJapanScraper,
    "legal-tools": LegalToolsScraper,
}


def format_case_output(case: CaseData, format_type: str = "text") -> str:
    """Format case data for output."""
    if format_type == "json":
        return json.dumps(
            {
                "case_name": case.case_name,
                "case_id": case.case_id,
                "court": case.court,
                "date": case.date.isoformat() if case.date else None,
                "url": case.url,
                "summary": case.summary,
                "jurisdiction": case.jurisdiction,
                "citations": case.citations,
                "judges": case.judges,
                "parties": case.parties,
                "legal_issues": case.legal_issues,
                "case_type": case.case_type,
                "metadata": case.metadata,
            },
            indent=2,
            ensure_ascii=False,
        )
    elif format_type == "csv":
        return f'"{case.case_name}","{case.case_id}","{case.court}","{case.date}","{case.url}","{case.jurisdiction}"'
    else:  # text format
        output = []
        output.append(f"Case: {case.case_name}")
        output.append(f"ID: {case.case_id}")
        output.append(f"Court: {case.court}")
        output.append(f"Date: {case.date}")
        output.append(f"URL: {case.url}")
        output.append(f"Jurisdiction: {case.jurisdiction}")
        if case.citations:
            output.append(f"Citations: {', '.join(case.citations)}")
        if case.judges:
            output.append(f"Judges: {', '.join(case.judges)}")
        if case.parties:
            output.append(f"Parties: {', '.join(case.parties)}")
        if case.summary:
            output.append(f"Summary: {case.summary[:200]}...")
        output.append("-" * 80)
        return "\n".join(output)


def search_command(args) -> None:
    """Execute search command."""
    logger = setup_logger("cli", level=args.verbose)

    if args.scraper not in SCRAPERS:
        print(f"Error: Unknown scraper '{args.scraper}'", file=sys.stderr)
        print(f"Available scrapers: {', '.join(SCRAPERS.keys())}", file=sys.stderr)
        sys.exit(1)

    scraper_class = SCRAPERS[args.scraper]

    try:
        with scraper_class() as scraper:
            logger.info(f"Searching {args.scraper} for: {args.query}")

            cases = scraper.search_cases(
                query=args.query,
                start_date=args.start_date,
                end_date=args.end_date,
                court=args.court,
                limit=args.limit,
            )

            if not cases:
                print("No cases found.")
                return

            print(f"Found {len(cases)} cases:\n")

            for case in cases:
                output = format_case_output(case, args.format)
                print(output)

                if args.output:
                    with open(args.output, "a", encoding="utf-8") as f:
                        f.write(output + "\n")

            logger.info(f"Search completed. Found {len(cases)} cases.")

    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


def get_case_command(args) -> None:
    """Execute get case command."""
    logger = setup_logger("cli", level=args.verbose)

    if args.scraper not in SCRAPERS:
        print(f"Error: Unknown scraper '{args.scraper}'", file=sys.stderr)
        print(f"Available scrapers: {', '.join(SCRAPERS.keys())}", file=sys.stderr)
        sys.exit(1)

    scraper_class = SCRAPERS[args.scraper]

    try:
        with scraper_class() as scraper:
            logger.info(f"Getting case {args.case_id} from {args.scraper}")

            case = scraper.get_case_by_id(args.case_id)

            if not case:
                print(f"Case '{args.case_id}' not found.")
                return

            output = format_case_output(case, args.format)
            print(output)

            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(output)

            logger.info(f"Case retrieval completed.")

    except Exception as e:
        logger.error(f"Case retrieval failed: {str(e)}")
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


def list_scrapers_command(args) -> None:
    """List available scrapers."""
    print("Available scrapers:")
    print("=" * 50)

    scraper_info = {
        "courtlistener": "CourtListener (US federal and state case law)",
        "findlaw": "FindLaw (US Supreme Court and state case law)",
        "austlii": "AustLII (Australian case law)",
        "canlii": "CanLII (Canadian case law)",
        "bailii": "BAILII (UK and Ireland case law)",
        "singapore": "Singapore Judiciary (Singapore case law)",
        "indian-kanoon": "Indian Kanoon (Indian case law)",
        "hklii": "HKLII (Hong Kong case law)",
        "legifrance": "Légifrance (French case law)",
        "german-law": "German Law Archive (German case law)",
        "curia-europa": "Curia Europa (EU case law)",
        "worldlii": "WorldLII (International case law)",
        "worldcourts": "WorldCourts (International case law)",
        "supremecourt-india": "Supreme Court of India",
        "kenya-law": "Kenya Law (Kenyan case law)",
        "supremecourt-japan": "Supreme Court of Japan",
        "legal-tools": "ICC Legal Tools Database",
    }

    for scraper_name, description in scraper_info.items():
        print(f"{scraper_name:20} - {description}")


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        prog="junior-associate",
        description="The Junior Associate - Legal case law scraper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  junior-associate search courtlistener "privacy rights" --limit 10
  junior-associate search canlii "charter rights" --start-date 2023-01-01
  junior-associate get-case courtlistener "12345"
  junior-associate list-scrapers
        """,
    )

    parser.add_argument(
        "--version", action="version", version="The Junior Associate 1.0.0"
    )
    parser.add_argument(
        "--verbose", "-v", action="count", default=0, help="Increase verbosity"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Search command
    search_parser = subparsers.add_parser("search", help="Search for cases")
    search_parser.add_argument("scraper", help="Scraper to use")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument(
        "--start-date", help="Start date (YYYY-MM-DD)", type=str
    )
    search_parser.add_argument("--end-date", help="End date (YYYY-MM-DD)", type=str)
    search_parser.add_argument("--court", help="Court name or code", type=str)
    search_parser.add_argument(
        "--limit", help="Maximum number of results", type=int, default=20
    )
    search_parser.add_argument(
        "--format",
        choices=["text", "json", "csv"],
        default="text",
        help="Output format",
    )
    search_parser.add_argument("--output", "-o", help="Output file", type=str)
    search_parser.set_defaults(func=search_command)

    # Get case command
    get_parser = subparsers.add_parser("get-case", help="Get specific case by ID")
    get_parser.add_argument("scraper", help="Scraper to use")
    get_parser.add_argument("case_id", help="Case ID")
    get_parser.add_argument(
        "--format",
        choices=["text", "json", "csv"],
        default="text",
        help="Output format",
    )
    get_parser.add_argument("--output", "-o", help="Output file", type=str)
    get_parser.set_defaults(func=get_case_command)

    # List scrapers command
    list_parser = subparsers.add_parser("list-scrapers", help="List available scrapers")
    list_parser.set_defaults(func=list_scrapers_command)

    return parser


def main() -> None:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Set verbosity level
    if args.verbose >= 2:
        import logging
        verbosity = logging.DEBUG
    elif args.verbose >= 1:
        import logging
        verbosity = logging.INFO
    else:
        import logging
        verbosity = logging.WARNING

    args.verbose = verbosity

    # Execute command
    args.func(args)


if __name__ == "__main__":
    main()