from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo

import requests

from src.canvas_client import Assignment


class IcalClient:
    def __init__(self, ical_url: str, default_timezone: str = "America/New_York") -> None:
        self.ical_url = ical_url
        self.default_timezone = default_timezone

    def get_upcoming_assignments(self) -> list[Assignment]:
        response = requests.get(self.ical_url, timeout=20)
        response.raise_for_status()
        return parse_canvas_ical(response.text, self.default_timezone)


def parse_canvas_ical(ics_text: str, default_timezone: str = "America/New_York") -> list[Assignment]:
    lines = _unfold_lines(ics_text)
    events = _extract_events(lines)
    assignments: list[Assignment] = []
    default_tz = ZoneInfo(default_timezone)

    for event in events:
        due_prop = _extract_property_with_params(event, "DUE")
        if due_prop is None:
            due_prop = _extract_property_with_params(event, "DTSTART")
        if due_prop is None:
            continue
        due_at = _parse_ical_datetime(due_prop["value"], due_prop["params"], default_tz)
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


def _extract_property_with_params(
    event_lines: list[str], prop_name: str
) -> Optional[dict[str, object]]:
    prefix = f"{prop_name}:"
    param_prefix = f"{prop_name};"
    for line in event_lines:
        if line.startswith(prefix):
            return {"value": line[len(prefix) :].strip(), "params": {}}
        if line.startswith(param_prefix):
            left, value = line.split(":", 1)
            params: dict[str, str] = {}
            for part in left.split(";")[1:]:
                if "=" in part:
                    k, v = part.split("=", 1)
                    params[k.upper()] = v
            return {"value": value.strip(), "params": params}
    return None


def _parse_ical_datetime(
    raw_value: str, params: dict[str, str], default_tz: ZoneInfo
) -> Optional[datetime]:
    value = raw_value.strip()

    if params.get("VALUE", "").upper() == "DATE":
        try:
            local_date = datetime.strptime(value, "%Y%m%d").date()
        except ValueError:
            return None
        # Canvas date-only assignments are due by end of local day.
        end_of_day_local = datetime.combine(local_date, datetime.max.time(), default_tz)
        return end_of_day_local.astimezone(timezone.utc)

    if value.endswith("Z"):
        dt_str = value[:-1]
        for fmt in ("%Y%m%dT%H%M%S", "%Y%m%dT%H%M"):
            try:
                return datetime.strptime(dt_str, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        return None

    tzid = params.get("TZID")
    if tzid:
        try:
            tz = ZoneInfo(tzid)
        except Exception:
            tz = default_tz
    else:
        tz = default_tz

    for fmt in ("%Y%m%dT%H%M%S", "%Y%m%dT%H%M"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=tz).astimezone(
                timezone.utc
            )
        except ValueError:
            continue

    try:
        local_date = datetime.strptime(value, "%Y%m%d").date()
        end_of_day_local = datetime.combine(local_date, datetime.max.time(), tz)
        return end_of_day_local.astimezone(timezone.utc)
    except ValueError:
        return None


def _unescape_ical_text(value: str) -> str:
    return (
        value.replace("\\n", "\n")
        .replace("\\,", ",")
        .replace("\\;", ";")
        .replace("\\\\", "\\")
    )
