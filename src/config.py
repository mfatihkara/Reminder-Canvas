import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass
class Settings:
    canvas_ical_url: str
    canvas_base_url: str
    canvas_api_token: str
    notifier_mode: str
    notify_target: str
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    smtp_from_email: str
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_from_number: str
    timezone: str
    remind_days_ahead: int
    state_db_path: str

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            canvas_ical_url=os.getenv("CANVAS_ICAL_URL", ""),
            canvas_base_url=os.getenv("CANVAS_BASE_URL", "").rstrip("/"),
            canvas_api_token=os.getenv("CANVAS_API_TOKEN", ""),
            notifier_mode=os.getenv("NOTIFIER_MODE", "email_gateway").strip().lower(),
            notify_target=os.getenv("NOTIFY_TARGET", ""),
            smtp_host=os.getenv("SMTP_HOST", "smtp.gmail.com"),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            smtp_username=os.getenv("SMTP_USERNAME", ""),
            smtp_password=os.getenv("SMTP_PASSWORD", ""),
            smtp_from_email=os.getenv("SMTP_FROM_EMAIL", ""),
            twilio_account_sid=os.getenv("TWILIO_ACCOUNT_SID", ""),
            twilio_auth_token=os.getenv("TWILIO_AUTH_TOKEN", ""),
            twilio_from_number=os.getenv("TWILIO_FROM_NUMBER", ""),
            timezone=os.getenv("TIMEZONE", "America/New_York"),
            remind_days_ahead=int(os.getenv("REMIND_DAYS_AHEAD", "3")),
            state_db_path=os.getenv("STATE_DB_PATH", "state.db"),
        )

    def validate(self) -> None:
        required_fields = {"NOTIFY_TARGET": self.notify_target}
        missing = [k for k, v in required_fields.items() if not v]
        source_configured = bool(self.canvas_ical_url) or bool(
            self.canvas_base_url and self.canvas_api_token
        )
        if not source_configured:
            missing.append("CANVAS_ICAL_URL (or CANVAS_BASE_URL + CANVAS_API_TOKEN)")

        if self.notifier_mode == "email_gateway":
            email_required = {
                "SMTP_HOST": self.smtp_host,
                "SMTP_PORT": self.smtp_port,
                "SMTP_USERNAME": self.smtp_username,
                "SMTP_PASSWORD": self.smtp_password,
                "SMTP_FROM_EMAIL": self.smtp_from_email,
            }
            missing.extend([k for k, v in email_required.items() if not v])
        elif self.notifier_mode == "twilio":
            twilio_required = {
                "TWILIO_ACCOUNT_SID": self.twilio_account_sid,
                "TWILIO_AUTH_TOKEN": self.twilio_auth_token,
                "TWILIO_FROM_NUMBER": self.twilio_from_number,
            }
            missing.extend([k for k, v in twilio_required.items() if not v])
        else:
            missing.append("NOTIFIER_MODE must be 'email_gateway' or 'twilio'")

        if missing:
            missing_csv = ", ".join(missing)
            raise ValueError(f"Missing required environment variables: {missing_csv}")
