from datetime import datetime, timezone
from typing import Optional

import requests

from src.canvas_client import Assignment


class IcalClient:
    def __init__(self, ical_url: str) -> None:
        self.ical_url = ical_url

    def get_upcoming_assignments(self) -> list[Assignment]:
        response = requests.get(self.ical_url, timeout=20)
        response.raise_for_status()
        return parse_canvas_ical(response.text)


def parse_canvas_ical(ics_text: str) -> list[Assignment]:
    lines = _unfold_lines(ics_text)
    events = _extract_events(lines)
    assignments: list[Assignment] = []

    for event in events:
        due_at_raw = _extract_property(event, "DUE") or _extract_property(event, "DTSTART")
        if not due_at_raw:
            continue
        due_at = _parse_ical_datetime(due_at_raw)
        if due_at is None:
            continue

        uid = _extract_property(event, "UID") or f"{len(assignments)}"
        summary = _extract_property(event, "SUMMARY") or "Canvas Assignment"
        description = _extract_property(event, "DESCRIPTION") or ""
        url = _extract_property(event, "URL") or ""
        course_name = _extract_course_name(description)

        assignments.append(
            Assignment(
                id=_stable_int(uid),
                course_id=0,
                course_name=course_name,
                name=_unescape_ical_text(summary),
                due_at=due_at,
                html_url=url,
            )
        )

    return assignments


def _stable_int(value: str) -> int:
    result = 0
    for ch in value:
        result = (result * 31 + ord(ch)) & 0x7FFFFFFF
    return result or 1


def _extract_course_name(description: str) -> str:
    plain = _unescape_ical_text(description)
    for marker in ("Course:", "course:"):
        idx = plain.find(marker)
        if idx >= 0:
            suffix = plain[idx + len(marker) :].splitlines()[0].strip()
            if suffix:
                return suffix
    return "Canvas"


def _unfold_lines(ics_text: str) -> list[str]:
    raw_lines = ics_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    lines: list[str] = []
    for line in raw_lines:
        if not line:
            lines.append(line)
            continue
        if (line.startswith(" ") or line.startswith("\t")) and lines:
            lines[-1] = lines[-1] + line[1:]
        else:
            lines.append(line)
    return lines


def _extract_events(lines: list[str]) -> list[list[str]]:
    events: list[list[str]] = []
    current: list[str] = []
    in_event = False
    for line in lines:
        if line == "BEGIN:VEVENT":
            in_event = True
            current = []
            continue
        if line == "END:VEVENT":
            if in_event:
                events.append(current[:])
            in_event = False
            current = []
            continue
        if in_event:
            current.append(line)
    return events


def _extract_property(event_lines: list[str], prop_name: str) -> str:
    prefix = f"{prop_name}:"
    param_prefix = f"{prop_name};"
    for line in event_lines:
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
        if line.startswith(param_prefix):
            _, value = line.split(":", 1)
            return value.strip()
    return ""


def _parse_ical_datetime(raw_value: str) -> Optional[datetime]:
    value = raw_value.strip()
    if value.endswith("Z"):
        dt_str = value[:-1]
        for fmt in ("%Y%m%dT%H%M%S", "%Y%m%dT%H%M"):
            try:
                return datetime.strptime(dt_str, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        return None

    for fmt in ("%Y%m%dT%H%M%S", "%Y%m%dT%H%M"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    try:
        return datetime.strptime(value, "%Y%m%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _unescape_ical_text(value: str) -> str:
    return (
        value.replace("\\n", "\n")
        .replace("\\,", ",")
        .replace("\\;", ";")
        .replace("\\\\", "\\")
    )
