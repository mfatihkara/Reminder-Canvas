import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass
class Settings:
    canvas_base_url: str
    canvas_api_token: str
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_from_number: str
    to_number: str
    timezone: str
    remind_days_ahead: int
    state_db_path: str

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            canvas_base_url=os.getenv("CANVAS_BASE_URL", "").rstrip("/"),
            canvas_api_token=os.getenv("CANVAS_API_TOKEN", ""),
            twilio_account_sid=os.getenv("TWILIO_ACCOUNT_SID", ""),
            twilio_auth_token=os.getenv("TWILIO_AUTH_TOKEN", ""),
            twilio_from_number=os.getenv("TWILIO_FROM_NUMBER", ""),
            to_number=os.getenv("TO_NUMBER", ""),
            timezone=os.getenv("TIMEZONE", "America/New_York"),
            remind_days_ahead=int(os.getenv("REMIND_DAYS_AHEAD", "3")),
            state_db_path=os.getenv("STATE_DB_PATH", "state.db"),
        )

    def validate(self) -> None:
        required_fields = {
            "CANVAS_BASE_URL": self.canvas_base_url,
            "CANVAS_API_TOKEN": self.canvas_api_token,
            "TWILIO_ACCOUNT_SID": self.twilio_account_sid,
            "TWILIO_AUTH_TOKEN": self.twilio_auth_token,
            "TWILIO_FROM_NUMBER": self.twilio_from_number,
            "TO_NUMBER": self.to_number,
        }
        missing = [k for k, v in required_fields.items() if not v]
        if missing:
            missing_csv = ", ".join(missing)
            raise ValueError(f"Missing required environment variables: {missing_csv}")
