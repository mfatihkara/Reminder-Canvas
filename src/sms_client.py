from twilio.rest import Client


class SmsClient:
    def __init__(self, account_sid: str, auth_token: str, from_number: str) -> None:
        self.client = Client(account_sid, auth_token)
        self.from_number = from_number

    def send(self, to_number: str, message: str) -> str:
        result = self.client.messages.create(
            body=message,
            from_=self.from_number,
            to=to_number,
        )
        return result.sid
