from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ChangeType(str, Enum):
    STANDARD = "standard"
    NORMAL = "normal"
    EMERGENCY = "emergency"


class Risk(str, Enum):
    HIGH = "1"
    MODERATE = "2"
    LOW = "3"
    NONE = "4"


class Impact(str, Enum):
    HIGH = "1"
    MEDIUM = "2"
    LOW = "3"


class Priority(str, Enum):
    CRITICAL = "1"
    HIGH = "2"
    MODERATE = "3"
    LOW = "4"
    PLANNING = "5"


class ChangeState(str, Enum):
    NEW = "-5"
    ASSESS = "-4"
    AUTHORIZE = "-3"
    SCHEDULED = "-2"
    IMPLEMENT = "-1"
    REVIEW = "0"
    CLOSED = "3"
    CANCELED = "4"


class ChangeRequestCreate(BaseModel):
    """Fields for creating a new change request."""

    short_description: str = Field(..., description="Brief summary of the change")
    description: Optional[str] = Field(None, description="Detailed description of the change")
    type: ChangeType = Field(default=ChangeType.STANDARD, description="Change type: standard, normal, or emergency")
    category: Optional[str] = Field(None, description="Category of the change (e.g. 'Software', 'Hardware', 'Network')")
    risk: Risk = Field(default=Risk.LOW, description="Risk level: 1=High, 2=Moderate, 3=Low, 4=None")
    impact: Impact = Field(default=Impact.LOW, description="Impact level: 1=High, 2=Medium, 3=Low")
    priority: Priority = Field(default=Priority.MODERATE, description="Priority: 1=Critical through 5=Planning")
    assignment_group: Optional[str] = Field(None, description="Name or sys_id of the assignment group")
    assigned_to: Optional[str] = Field(None, description="User name or sys_id of the assignee")
    start_date: Optional[str] = Field(None, description="Planned start date (YYYY-MM-DD HH:MM:SS)")
    end_date: Optional[str] = Field(None, description="Planned end date (YYYY-MM-DD HH:MM:SS)")
    implementation_plan: Optional[str] = Field(None, description="Steps to implement the change")
    backout_plan: Optional[str] = Field(None, description="Steps to back out if the change fails")
    test_plan: Optional[str] = Field(None, description="Steps to test/verify the change")
    justification: Optional[str] = Field(None, description="Business justification for the change")
    std_change_producer_version: Optional[str] = Field(
        None, description="Sys_id of the standard change template/producer version"
    )

    def to_snow_payload(self) -> dict:
        """Convert to ServiceNow API payload, omitting None values."""
        field_map = {
            "short_description": "short_description",
            "description": "description",
            "type": "type",
            "category": "category",
            "risk": "risk",
            "impact": "impact",
            "priority": "priority",
            "assignment_group": "assignment_group",
            "assigned_to": "assigned_to",
            "start_date": "start_date",
            "end_date": "end_date",
            "implementation_plan": "implementation_plan",
            "backout_plan": "backout_plan",
            "test_plan": "test_plan",
            "justification": "justification",
            "std_change_producer_version": "std_change_producer_version",
        }
        payload: dict = {}
        for attr, snow_field in field_map.items():
            value = getattr(self, attr)
            if value is not None:
                payload[snow_field] = value.value if isinstance(value, Enum) else value
        return payload


class ChangeRequestUpdate(BaseModel):
    """Fields for updating an existing change request."""

    short_description: Optional[str] = Field(None, description="Updated summary")
    description: Optional[str] = Field(None, description="Updated description")
    state: Optional[ChangeState] = Field(None, description="New state for the change request")
    category: Optional[str] = Field(None, description="Updated category")
    risk: Optional[Risk] = Field(None, description="Updated risk level")
    impact: Optional[Impact] = Field(None, description="Updated impact level")
    priority: Optional[Priority] = Field(None, description="Updated priority")
    assignment_group: Optional[str] = Field(None, description="Updated assignment group")
    assigned_to: Optional[str] = Field(None, description="Updated assignee")
    start_date: Optional[str] = Field(None, description="Updated planned start date")
    end_date: Optional[str] = Field(None, description="Updated planned end date")
    implementation_plan: Optional[str] = Field(None, description="Updated implementation plan")
    backout_plan: Optional[str] = Field(None, description="Updated backout plan")
    test_plan: Optional[str] = Field(None, description="Updated test plan")
    close_code: Optional[str] = Field(None, description="Close code (e.g. 'successful')")
    close_notes: Optional[str] = Field(None, description="Close notes")

    def to_snow_payload(self) -> dict:
        """Convert to ServiceNow API payload, omitting None values."""
        payload: dict = {}
        for field_name, field_value in self:
            if field_value is not None:
                payload[field_name] = field_value.value if isinstance(field_value, Enum) else field_value
        return payload
