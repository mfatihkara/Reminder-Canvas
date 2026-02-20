from datetime import datetime, timedelta, timezone
from typing import Callable, Optional
from zoneinfo import ZoneInfo

from src.canvas_client import Assignment
from src.state_store import StateStore


def _hours_until_due(assignment: Assignment, now_utc: datetime) -> float:
    return (assignment.due_at - now_utc).total_seconds() / 3600.0


def _fmt_due_local(assignment: Assignment, tz: ZoneInfo) -> str:
    return assignment.due_at.astimezone(tz).strftime("%a %b %d, %I:%M %p")


def _build_threshold_message(assignment: Assignment, tz: ZoneInfo, label: str) -> str:
    due_text = _fmt_due_local(assignment, tz)
    return (
        f"Reminder ({label}): '{assignment.name}' for {assignment.course_name} is due "
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

    for assignment in upcoming:
        hours = _hours_until_due(assignment, current)
        local_due = assignment.due_at.astimezone(tz)
        assignment_key = f"{assignment.course_id}:{assignment.id}:{assignment.due_at.isoformat()}"

        if 71 <= hours <= 73:
            key = f"3d:{assignment_key}"
            if not state.already_sent(key):
                message = _build_threshold_message(assignment, tz, "due in 3 days")
                sid = send_sms(to_number, message)
                print(f"Sent 3-day reminder SMS: {sid} for assignment {assignment.id}")
                state.mark_sent(key)
                sent_count += 1

        if local_due.date() == local_now.date():
            key = f"today:{assignment_key}:{local_now.date().isoformat()}"
            if not state.already_sent(key):
                message = _build_threshold_message(assignment, tz, "due today")
                sid = send_sms(to_number, message)
                print(f"Sent due-today reminder SMS: {sid} for assignment {assignment.id}")
                state.mark_sent(key)
                sent_count += 1

        if 2.5 <= hours <= 3.5:
            key = f"3h:{assignment_key}"
            if not state.already_sent(key):
                message = _build_threshold_message(assignment, tz, "due in 3 hours")
                sid = send_sms(to_number, message)
                print(f"Sent 3-hour reminder SMS: {sid} for assignment {assignment.id}")
                state.mark_sent(key)
                sent_count += 1

    state.cleanup()
    return {"upcoming_assignments": len(upcoming), "sent_messages": sent_count}
