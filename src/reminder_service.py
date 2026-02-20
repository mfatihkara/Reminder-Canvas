from datetime import datetime, timedelta, timezone
from typing import Callable, Optional
from zoneinfo import ZoneInfo

from src.canvas_client import Assignment
from src.state_store import StateStore


def _hours_until_due(assignment: Assignment, now_utc: datetime) -> float:
    return (assignment.due_at - now_utc).total_seconds() / 3600.0


def _fmt_due_local(assignment: Assignment, tz: ZoneInfo) -> str:
    return assignment.due_at.astimezone(tz).strftime("%a %b %d, %I:%M %p")


def _build_digest_message(assignments: list[Assignment], tz: ZoneInfo, days_ahead: int) -> str:
    upcoming = sorted(assignments, key=lambda a: a.due_at)
    lines = [f"Canvas deadlines in next {days_ahead} day(s):"]
    for assignment in upcoming:
        lines.append(
            f"- {assignment.course_name}: {assignment.name} @ {_fmt_due_local(assignment, tz)}"
        )
    return "\n".join(lines[:8])


def _build_24h_message(assignment: Assignment, tz: ZoneInfo) -> str:
    due_text = _fmt_due_local(assignment, tz)
    return (
        f"Reminder: '{assignment.name}' for {assignment.course_name} is due in about 24h "
        f"({due_text}). {assignment.html_url}".strip()
    )


def run_once(
    assignments: list[Assignment],
    state: StateStore,
    send_sms: Callable[[str, str], str],
    to_number: str,
    timezone_name: str,
    remind_days_ahead: int,
    now_utc: Optional[datetime] = None,
) -> dict[str, int]:
    tz = ZoneInfo(timezone_name)
    current = now_utc or datetime.now(timezone.utc)
    upcoming_cutoff = current + timedelta(days=remind_days_ahead)

    upcoming = [a for a in assignments if current <= a.due_at <= upcoming_cutoff]
    sent_count = 0

    local_now = current.astimezone(tz)
    digest_key = f"digest:{local_now.date().isoformat()}"
    if local_now.hour == 8 and not state.already_sent(digest_key):
        if upcoming:
            sid = send_sms(to_number, _build_digest_message(upcoming, tz, remind_days_ahead))
            print(f"Sent daily digest SMS: {sid}")
        else:
            sid = send_sms(to_number, "No Canvas deadlines in your reminder window.")
            print(f"Sent no-deadlines SMS: {sid}")
        state.mark_sent(digest_key)
        sent_count += 1

    for assignment in upcoming:
        hours = _hours_until_due(assignment, current)
        if not (23 <= hours <= 25):
            continue
        key = f"24h:{assignment.course_id}:{assignment.id}:{assignment.due_at.isoformat()}"
        if state.already_sent(key):
            continue
        message = _build_24h_message(assignment, tz)
        sid = send_sms(to_number, message)
        print(f"Sent 24h reminder SMS: {sid} for assignment {assignment.id}")
        state.mark_sent(key)
        sent_count += 1

    state.cleanup()
    return {"upcoming_assignments": len(upcoming), "sent_messages": sent_count}
