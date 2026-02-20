import smtplib
from email.message import EmailMessage


class EmailClient:
    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_username: str,
        smtp_password: str,
        from_email: str,
    ) -> None:
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
        self.from_email = from_email

    def send(self, to_email: str, message: str) -> str:
        email = EmailMessage()
        email["Subject"] = "Canvas Deadline Reminder"
        email["From"] = self.from_email
        email["To"] = to_email
        email.set_content(message)

        with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=20) as server:
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            server.send_message(email)

        return "smtp-sent"
