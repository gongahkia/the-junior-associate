"""
Tests for data models.
"""

import pytest
from datetime import datetime

from the_junior_associate.utils.data_models import CaseData


class TestCaseData:
    """Tests for CaseData model."""

    def test_case_data_creation(self):
        """Test basic CaseData creation."""
        case = CaseData(
            case_name="Test Case",
            case_id="TEST-001",
            court="Test Court",
            date=datetime(2023, 1, 15),
            url="https://example.com/test-001",
            jurisdiction="Test Jurisdiction",
        )

        assert case.case_name == "Test Case"
        assert case.case_id == "TEST-001"
        assert case.court == "Test Court"
        assert case.date == datetime(2023, 1, 15)
        assert case.url == "https://example.com/test-001"
        assert case.jurisdiction == "Test Jurisdiction"

    def test_case_data_optional_fields(self):
        """Test CaseData with optional fields."""
        case = CaseData(
            case_name="Test Case",
            case_id="TEST-001",
            summary="Test summary",
            judges=["Judge A", "Judge B"],
            parties=["Party 1", "Party 2"],
            citations=["2023 TC 1"],
            legal_issues=["Contract Law"],
            case_type="Civil",
            metadata={"source": "TestScraper"},
        )

        assert case.summary == "Test summary"
        assert case.judges == ["Judge A", "Judge B"]
        assert case.parties == ["Party 1", "Party 2"]
        assert case.citations == ["2023 TC 1"]
        assert case.legal_issues == ["Contract Law"]
        assert case.case_type == "Civil"
        assert case.metadata == {"source": "TestScraper"}

    def test_case_data_defaults(self):
        """Test CaseData default values."""
        case = CaseData(case_name="Test Case")

        assert case.case_id is None
        assert case.court is None
        assert case.date is None
        assert case.url is None
        assert case.summary is None
        assert case.full_text is None
        assert case.judges == []
        assert case.parties == []
        assert case.citations == []
        assert case.legal_issues == []
        assert case.case_type is None
        assert case.jurisdiction is None
        assert case.metadata == {}

    def test_case_data_repr(self):
        """Test CaseData string representation."""
        case = CaseData(
            case_name="Test Case v. Example",
            case_id="TEST-001",
            court="Test Court",
        )

        repr_str = repr(case)
        assert "Test Case v. Example" in repr_str
        assert "TEST-001" in repr_str

    def test_case_data_equality(self):
        """Test CaseData equality comparison."""
        case1 = CaseData(case_name="Test Case", case_id="TEST-001")
        case2 = CaseData(case_name="Test Case", case_id="TEST-001")
        case3 = CaseData(case_name="Different Case", case_id="TEST-002")

        assert case1 == case2
        assert case1 != case3

    def test_case_data_immutable_lists(self):
        """Test that list fields are properly initialized."""
        case = CaseData(case_name="Test Case")

        # Should be able to append to lists
        case.judges.append("Judge A")
        assert "Judge A" in case.judges

        case.parties.append("Party 1")
        assert "Party 1" in case.parties

        case.citations.append("2023 TC 1")
        assert "2023 TC 1" in case.citations

        case.legal_issues.append("Contract Law")
        assert "Contract Law" in case.legal_issues
