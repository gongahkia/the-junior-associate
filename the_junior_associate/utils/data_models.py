"""
Data models for The Junior Associate library.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Any


@dataclass
class CaseData:
    """
    Standardized data structure for legal case information.
    """

    case_name: str
    case_id: Optional[str] = None
    court: Optional[str] = None
    date: Optional[datetime] = None
    url: Optional[str] = None
    full_text: Optional[str] = None
    summary: Optional[str] = None
    judges: Optional[List[str]] = field(default_factory=list)
    parties: Optional[List[str]] = field(default_factory=list)
    legal_issues: Optional[List[str]] = field(default_factory=list)
    citations: Optional[List[str]] = field(default_factory=list)
    jurisdiction: Optional[str] = None
    case_type: Optional[str] = None
    outcome: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the case data to a dictionary."""
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()
            elif value is not None:
                result[key] = value
        return result

    def __str__(self) -> str:
        """String representation of the case."""
        parts = [f"Case: {self.case_name}"]
        if self.court:
            parts.append(f"Court: {self.court}")
        if self.date:
            parts.append(f"Date: {self.date.strftime('%Y-%m-%d')}")
        if self.case_id:
            parts.append(f"ID: {self.case_id}")
        return " | ".join(parts)

    def __repr__(self) -> str:
        """Detailed representation of the case."""
        return (
            f"CaseData(case_name='{self.case_name}', "
            f"case_id='{self.case_id}', "
            f"court='{self.court}', "
            f"date={self.date}, "
            f"jurisdiction='{self.jurisdiction}')"
        )