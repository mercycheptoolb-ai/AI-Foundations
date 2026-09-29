"""Pydantic models shared by the agent and its tools."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Course(BaseModel):
    """One row of data/yale_som_classes.json (raw keys are mapped via aliases)."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    course_id: str = Field("", alias="Course ID")
    number: str = Field("", alias="Course Number")
    title: str = Field("", alias="Course Title")
    section: str = Field("", alias="Section")
    category: str = Field("", alias="Course Category")
    course_type: str = Field("", alias="Course Type")
    bid_or_permission: str = Field("", alias="Bid Or Permission")
    session: str = Field("", alias="Course Session")
    term_code: str = Field("", alias="TermCode")
    start_date: str = Field("", alias="Course Session Start date")
    end_date: str = Field("", alias="Course Session End Date")
    day_time: str = Field("", alias="Daytimes")
    room: str = Field("", alias="Room")
    units: str = Field("", alias="Units")
    faculty: str = Field("", alias="Faculty 1")
    faculty_email: str = Field("", alias="Faculty 1 Email")
    syllabus: str = Field("", alias="Syllabus")
    old_syllabus: str = Field("", alias="Old Syllabus")
    description: str = Field("", alias="Course Description")
    faculty_bio: str = Field("", alias="faculty_bio")
    visible: str = Field("", alias="Visible")

    def for_agent(self, max_description: int = 500, max_bio: int = 300) -> dict[str, str]:
        """Compact dict for tool output; long text is trimmed to keep the prompt small."""
        return {
            "number": self.number,
            "section": self.section,
            "title": self.title,
            "faculty": self.faculty,
            "category": self.category,
            "type": self.course_type,
            "bid_or_permission": self.bid_or_permission,
            "session": self.session,
            "day_time": self.day_time,
            "room": self.room,
            "units": self.units,
            "syllabus": self.syllabus or self.old_syllabus,
            "description": _clip(self.description, max_description),
            "faculty_bio": _clip(self.faculty_bio, max_bio),
        }


class CourseSearchResult(BaseModel):
    """What search_courses returns to the model."""

    total_matches: int
    returned: int
    note: str = ""
    courses: list[dict[str, str]] = Field(default_factory=list)


class AgentResult(BaseModel):
    reply: str
    tools_used: list[str] = Field(default_factory=list)


def _clip(text: str, limit: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"
