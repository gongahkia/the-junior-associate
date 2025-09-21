"""
Pytest configuration and fixtures for The Junior Associate tests.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock
import requests

from the_junior_associate.utils.data_models import CaseData


@pytest.fixture
def sample_case_data():
    """Sample CaseData for testing."""
    return CaseData(
        case_name="Test Case v. Example Corp",
        case_id="TEST-2023-001",
        court="Test Supreme Court",
        date=datetime(2023, 1, 15),
        url="https://example.com/cases/test-2023-001",
        summary="This is a test case summary.",
        full_text="This is the full text of the test case...",
        judges=["Judge Smith", "Judge Johnson"],
        parties=["Test Case", "Example Corp"],
        citations=["2023 TSC 1", "[2023] TSC 001"],
        legal_issues=["Contract Law", "Tort Law"],
        case_type="Civil Appeal",
        jurisdiction="Test Jurisdiction",
        metadata={"source": "TestScraper", "scraped_at": "2023-01-15T10:00:00Z"},
    )


@pytest.fixture
def mock_response():
    """Mock HTTP response."""
    response = Mock(spec=requests.Response)
    response.status_code = 200
    response.text = """
    <html>
        <head><title>Test Case v. Example Corp</title></head>
        <body>
            <h1>Test Case v. Example Corp</h1>
            <div class="case-content">
                <p>This is a test case from Test Supreme Court.</p>
                <p>Date: January 15, 2023</p>
                <p>Judge: Judge Smith</p>
            </div>
        </body>
    </html>
    """
    response.headers = {"Content-Type": "text/html"}
    return response


@pytest.fixture
def mock_scraper_session():
    """Mock scraper session."""
    session = MagicMock()
    session.get.return_value.status_code = 200
    session.get.return_value.text = """
    <html>
        <head><title>Test Case</title></head>
        <body><div>Test content</div></body>
    </html>
    """
    return session


@pytest.fixture
def sample_search_results():
    """Sample search results."""
    return [
        {
            "case_name": "Case One v. Party One",
            "case_id": "CASE-001",
            "url": "https://example.com/case-001",
            "court": "Test Court",
            "date": "2023-01-01",
        },
        {
            "case_name": "Case Two v. Party Two",
            "case_id": "CASE-002",
            "url": "https://example.com/case-002",
            "court": "Test Court",
            "date": "2023-01-02",
        },
    ]
