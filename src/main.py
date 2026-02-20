import argparse
import time
from datetime import datetime, timezone
from typing import Callable, Tuple
from zoneinfo import ZoneInfo

from src.canvas_client import CanvasClient
from src.canvas_client import Assignment
from src.config import Settings
from src.email_client import EmailClient
from src.ical_client import IcalClient
from src.reminder_service import run_once
from src.sms_client import SmsClient
from src.state_store import StateStore


def _build_sender(settings: Settings, dry_run: bool) -> Tuple[Callable[[str, str], str], str]:
    if settings.notifier_mode == "email_gateway":
        email_client = EmailClient(
            smtp_host=settings.smtp_host,
            smtp_port=settings.smtp_port,
            smtp_username=settings.smtp_username,
            smtp_password=settings.smtp_password,
            from_email=settings.smtp_from_email,
        )
        notifier_label = "email gateway"
    else:
        sms_client = SmsClient(
            settings.twilio_account_sid,
            settings.twilio_auth_token,
            settings.twilio_from_number,
        )
        notifier_label = "twilio"

    def send_notification(target: str, message: str) -> str:
        if dry_run:
            print(f"[DRY RUN] Would send via {notifier_label} to {target}:")
            print(message)
            return "dry-run"
        if settings.notifier_mode == "email_gateway":
            return email_client.send(target, message)
        return sms_client.send(target, message)

    return send_notification, notifier_label


def _fetch_assignments(settings: Settings) -> Tuple[list[Assignment], str]:
    if settings.canvas_ical_url:
        source_label = "Canvas iCal feed"
        source_client = IcalClient(settings.canvas_ical_url, settings.timezone)
    else:
        source_label = "Canvas API"
        source_client = CanvasClient(settings.canvas_base_url, settings.canvas_api_token)
    assignments = source_client.get_upcoming_assignments()
    return assignments, source_label


def send_today_now(settings: Settings, dry_run: bool) -> None:
    send_notification, _ = _build_sender(settings, dry_run)
    assignments, source_label = _fetch_assignments(settings)
    print(f"Fetched {len(assignments)} assignments from {source_label}.")

    tz = ZoneInfo(settings.timezone)
    now_utc = datetime.now(timezone.utc)
    now_local = now_utc.astimezone(tz)
    end_of_day_local = datetime.combine(now_local.date(), datetime.max.time(), tz)
    end_of_day_utc = end_of_day_local.astimezone(timezone.utc)

    due_today = [a for a in assignments if now_utc <= a.due_at <= end_of_day_utc]
    due_today = sorted(due_today, key=lambda a: a.due_at)

    if due_today:
        lines = [f"Today's Canvas deadlines ({now_local.strftime('%a %b %d')}):"]
        for assignment in due_today[:8]:
            due_text = assignment.due_at.astimezone(tz).strftime("%I:%M %p")
            lines.append(f"- {assignment.course_name}: {assignment.name} @ {due_text}")
        message = "\n".join(lines)
    else:
        message = "No homework due today based on Canvas."

    sid = send_notification(settings.notify_target, message)
    print(f"Sent immediate today summary: {sid}")


def run_job(settings: Settings, dry_run: bool) -> None:
    state = StateStore(settings.state_db_path)
    send_notification, _ = _build_sender(settings, dry_run)
    assignments, source_label = _fetch_assignments(settings)
    print(f"Fetched {len(assignments)} assignments from {source_label}.")
    result = run_once(
        assignments=assignments,
        state=state,
        send_sms=send_notification,
        to_number=settings.notify_target,
        timezone_name=settings.timezone,
        remind_days_ahead=settings.remind_days_ahead,
        now_utc=datetime.now(timezone.utc),
    )
    print(result)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Canvas -> SMS deadline reminder service",
    )
    parser.add_argument(
        "--mode",
        choices=["once", "loop"],
        default="once",
        help="Run one check or keep polling in a loop.",
    )
    parser.add_argument(
        "--interval-minutes",
        type=int,
        default=30,
        help="Polling interval when --mode loop.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do everything except calling Twilio send.",
    )
    parser.add_argument(
        "--send-today-now",
        action="store_true",
        help="Send an immediate summary of assignments due today.",
    )
    args = parser.parse_args()

    settings = Settings.from_env()
    settings.validate()

    if args.send_today_now:
        send_today_now(settings, dry_run=args.dry_run)
        return

    if args.mode == "once":
        run_job(settings, dry_run=args.dry_run)
        return

    while True:
        try:
            run_job(settings, dry_run=args.dry_run)
        except Exception as exc:
            print(f"Reminder loop error: {exc}")
        time.sleep(args.interval_minutes * 60)


if __name__ == "__main__":
    main()
