"""Pydantic data objects shared by tools.py and agent.py."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Course(BaseModel):
    """One row of data/yale_som_classes.json (JSON keys are the aliases)."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    course_id: str = Field("", alias="Course ID")
    number: str = Field("", alias="Course Number")
    section: str = Field("", alias="Section")
    title: str = Field("", alias="Course Title")
    description: str = Field("", alias="Course Description")
    category: str = Field("", alias="Course Category")
    course_type: str = Field("", alias="Course Type")
    session: str = Field("", alias="Course Session")
    session_start: str = Field("", alias="Course Session Start date")
    session_end: str = Field("", alias="Course Session End Date")
    daytimes: str = Field("", alias="Daytimes")
    day: str = Field("", alias="Timings Day")
    start_time: str = Field("", alias="Timings StartTime")
    end_time: str = Field("", alias="Timings EndTime")
    room: str = Field("", alias="Room")
    units: str = Field("", alias="Units")
    bid_or_permission: str = Field("", alias="Bid Or Permission")
    faculty: str = Field("", alias="Faculty 1")
    faculty_email: str = Field("", alias="Faculty 1 Email")
    faculty_bio: str = Field("", alias="faculty_bio")
    syllabus: str = Field("", alias="Syllabus")
    old_syllabus: str = Field("", alias="Old Syllabus")

    @field_validator("*", mode="before")
    @classmethod
    def _to_clean_str(cls, value: Any) -> str:
        return "" if value is None else str(value).strip()


class SearchResult(BaseModel):
    """What search_courses hands back to the agent."""

    query: dict[str, str] = Field(default_factory=dict)
    total_matches: int = 0
    returned: int = 0
    truncated: bool = False
    courses: list[Course] = Field(default_factory=list)


class ToolCallRecord(BaseModel):
    name: str
    args: dict[str, Any] | str | None = None
    result: str = ""


class AuditEntry(BaseModel):
    """One agent loop in output/audit_trail.json."""

    time: str
    user_message: str
    thoughts: list[str] = Field(default_factory=list)
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)
    reply: str = ""
    stop_reason: str = ""


class AgentResult(BaseModel):
    """Shape main.py expects from run_agent()."""

    reply: str
    tools_used: list[str] = Field(default_factory=list)
