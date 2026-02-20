from datetime import datetime, timezone
from typing import Callable, Tuple
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from src.canvas_client import Assignment
from src.canvas_client import CanvasClient
from src.config import Settings
from src.email_client import EmailClient
from src.ical_client import IcalClient
from src.reminder_service import run_once
from src.sms_client import SmsClient
from src.state_store import StateStore


app = FastAPI(title="Canvas Reminder Dashboard")
templates = Jinja2Templates(directory="web/templates")


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
        targets = [t.strip() for t in target.split(",") if t.strip()]
        if not targets:
            raise ValueError("No notification target configured")
        if dry_run:
            return "dry-run"
        message_ids = []
        for t in targets:
            if settings.notifier_mode == "email_gateway":
                message_ids.append(email_client.send(t, message))
            else:
                message_ids.append(sms_client.send(t, message))
        return ",".join(message_ids)

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


def _due_today(assignments: list[Assignment], timezone_name: str) -> list[Assignment]:
    tz = ZoneInfo(timezone_name)
    now_utc = datetime.now(timezone.utc)
    now_local = now_utc.astimezone(tz)
    end_of_day_local = datetime.combine(now_local.date(), datetime.max.time(), tz)
    end_of_day_utc = end_of_day_local.astimezone(timezone.utc)
    due_today = [a for a in assignments if now_utc <= a.due_at <= end_of_day_utc]
    return sorted(due_today, key=lambda a: a.due_at)


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request) -> HTMLResponse:
    settings = Settings.from_env()
    settings.validate()
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "notifier_mode": settings.notifier_mode,
            "target": settings.notify_target,
            "timezone": settings.timezone,
        },
    )


@app.get("/api/status")
def status() -> JSONResponse:
    settings = Settings.from_env()
    settings.validate()
    assignments, source_label = _fetch_assignments(settings)
    due_today = _due_today(assignments, settings.timezone)
    tz = ZoneInfo(settings.timezone)
    payload = {
        "source": source_label,
        "total_assignments": len(assignments),
        "due_today_count": len(due_today),
        "due_today": [
            {
                "course": a.course_name,
                "name": a.name,
                "due_local": a.due_at.astimezone(tz).strftime("%a %b %d, %I:%M %p"),
            }
            for a in due_today[:8]
        ],
    }
    return JSONResponse(payload)


@app.post("/api/send-today-now")
def send_today_now() -> JSONResponse:
    settings = Settings.from_env()
    settings.validate()
    send_notification, notifier_label = _build_sender(settings, dry_run=False)
    assignments, _ = _fetch_assignments(settings)
    due_today = _due_today(assignments, settings.timezone)
    tz = ZoneInfo(settings.timezone)
    now_local = datetime.now(timezone.utc).astimezone(tz)

    if not due_today:
        sid = send_notification(settings.notify_target, "No homework due today based on Canvas.")
        return JSONResponse(
            {
                "ok": True,
                "delivery": notifier_label,
                "target": settings.notify_target,
                "message_id": sid,
                "sent_count": 1,
                "preview": "No homework due today based on Canvas.",
            }
        )

    stamp = now_local.strftime("%H:%M")
    message_ids = []
    previews = []
    for assignment in due_today[:8]:
        due_text = assignment.due_at.astimezone(tz).strftime("%I:%M %p")
        name = assignment.name[:80]
        course = assignment.course_name[:24]
        message = f"Due today {due_text}: {name} ({course}) [{stamp}]"
        previews.append(message)
        sid = send_notification(settings.notify_target, message)
        message_ids.append(sid)
    return JSONResponse(
        {
            "ok": True,
            "delivery": notifier_label,
            "target": settings.notify_target,
            "message_id": ",".join(message_ids),
            "sent_count": len(previews),
            "preview": "\n".join(previews),
        }
    )


@app.post("/api/run-once")
def run_check_once() -> JSONResponse:
    settings = Settings.from_env()
    settings.validate()
    state = StateStore(settings.state_db_path)
    send_notification, notifier_label = _build_sender(settings, dry_run=False)
    assignments, source_label = _fetch_assignments(settings)
    result = run_once(
        assignments=assignments,
        state=state,
        send_sms=send_notification,
        to_number=settings.notify_target,
        timezone_name=settings.timezone,
        remind_days_ahead=settings.remind_days_ahead,
        now_utc=datetime.now(timezone.utc),
    )
    return JSONResponse(
        {
            "ok": True,
            "source": source_label,
            "delivery": notifier_label,
            "result": result,
        }
    )
