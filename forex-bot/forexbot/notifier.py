"""التنبيهات: الطرفية دائماً، وتيليجرام اختيارياً (TELEGRAM_BOT_TOKEN و TELEGRAM_CHAT_ID)."""
from __future__ import annotations

import logging
import os

from . import net

log = logging.getLogger(__name__)


class Notifier:
    def __init__(self, telegram: bool = True):
        self.token = os.environ.get("TELEGRAM_BOT_TOKEN")
        self.chat = os.environ.get("TELEGRAM_CHAT_ID")
        self.telegram = telegram and bool(self.token and self.chat)

    def send(self, text: str) -> None:
        print(text, flush=True)
        if self.telegram:
            try:
                net.post_form(f"https://api.telegram.org/bot{self.token}/sendMessage",
                              {"chat_id": self.chat, "text": text})
            except Exception as e:
                log.warning("فشل إرسال تيليجرام: %s", e)
