import smtplib
from email.message import EmailMessage

import httpx

from hawk_worker.config import ScannerSettings
from hawk_worker.models import NotificationMessage


class NotificationService:
    def __init__(self, settings: ScannerSettings) -> None:
        self.settings = settings

    @staticmethod
    def render(message: NotificationMessage) -> str:
        rank = f"\nRanking position: #{message.ranking_position}" if message.ranking_position else ""
        return (f"HAWK SCANNER ALERT\n\n{message.symbol} reached Hawk Score {message.score:.2f}/100 "
                f"(threshold: {message.threshold:.2f}).\nConfidence: {message.confidence:.2%}{rank}")

    async def telegram(self, message: NotificationMessage) -> tuple[str, str, bool, str | None] | None:
        if not self.settings.telegram_bot_token or not self.settings.telegram_chat_id:
            return None
        destination = self.settings.telegram_chat_id
        url = f"https://api.telegram.org/bot{self.settings.telegram_bot_token}/sendMessage"
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(url, json={"chat_id": destination, "text": self.render(message)})
                response.raise_for_status()
            return "TELEGRAM", destination, True, None
        except Exception as error:
            return "TELEGRAM", destination, False, str(error)

    async def discord(self, message: NotificationMessage) -> tuple[str, str, bool, str | None] | None:
        if not self.settings.discord_webhook_url:
            return None
        destination = self.settings.discord_webhook_url
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(destination, json={"content": self.render(message)})
                response.raise_for_status()
            return "DISCORD", destination, True, None
        except Exception as error:
            return "DISCORD", destination, False, str(error)

    async def email(self, message: NotificationMessage) -> list[tuple[str, str, bool, str | None]]:
        if not self.settings.smtp_host or not self.settings.smtp_from or not self.settings.alert_email_to:
            return []
        rendered = self.render(message)
        outcome: list[tuple[str, str, bool, str | None]] = []
        for destination in self.settings.alert_email_to:
            email = EmailMessage()
            email["From"], email["To"], email["Subject"] = self.settings.smtp_from, destination, f"HAWK Score alert: {message.symbol}"
            email.set_content(rendered)
            try:
                with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port, timeout=20) as smtp:
                    smtp.starttls()
                    if self.settings.smtp_username and self.settings.smtp_password:
                        smtp.login(self.settings.smtp_username, self.settings.smtp_password)
                    smtp.send_message(email)
                outcome.append(("EMAIL", destination, True, None))
            except Exception as error:
                outcome.append(("EMAIL", destination, False, str(error)))
        return outcome
