import argparse
import time
from datetime import datetime, timezone

from src.canvas_client import CanvasClient
from src.config import Settings
from src.email_client import EmailClient
from src.ical_client import IcalClient
from src.reminder_service import run_once
from src.sms_client import SmsClient
from src.state_store import StateStore


def run_job(settings: Settings, dry_run: bool) -> None:
    state = StateStore(settings.state_db_path)

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

    if settings.canvas_ical_url:
        source_label = "Canvas iCal feed"
        source_client = IcalClient(settings.canvas_ical_url)
    else:
        source_label = "Canvas API"
        source_client = CanvasClient(settings.canvas_base_url, settings.canvas_api_token)

    assignments = source_client.get_upcoming_assignments()
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
    args = parser.parse_args()

    settings = Settings.from_env()
    settings.validate()

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
