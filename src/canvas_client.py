from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

import requests


@dataclass
class Assignment:
    id: int
    course_id: int
    course_name: str
    name: str
    due_at: datetime
    html_url: str


class CanvasClient:
    def __init__(self, base_url: str, api_token: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {api_token}"})

    def _request(self, path: str, params: Optional[dict[str, Any]] = None) -> Any:
        url = f"{self.base_url}{path}"
        response = self.session.get(url, params=params, timeout=20)
        response.raise_for_status()
        return response.json()

    def get_courses(self) -> list[dict[str, Any]]:
        return self._request(
            "/api/v1/courses",
            params={
                "enrollment_state": "active",
                "state[]": ["available"],
                "per_page": 100,
            },
        )

    def get_upcoming_assignments(self) -> list[Assignment]:
        courses = self.get_courses()
        assignments: list[Assignment] = []
        for course in courses:
            course_id = course.get("id")
            if not course_id:
                continue
            course_name = course.get("name", f"Course {course_id}")
            raw_assignments = self._request(
                f"/api/v1/courses/{course_id}/assignments",
                params={"bucket": "upcoming", "per_page": 100},
            )
            for raw in raw_assignments:
                due_at = raw.get("due_at")
                if not due_at:
                    continue
                parsed_due_at = datetime.fromisoformat(due_at.replace("Z", "+00:00"))
                assignments.append(
                    Assignment(
                        id=raw["id"],
                        course_id=course_id,
                        course_name=course_name,
                        name=raw.get("name", "Untitled Assignment"),
                        due_at=parsed_due_at,
                        html_url=raw.get("html_url", ""),
                    )
                )
        return assignments
