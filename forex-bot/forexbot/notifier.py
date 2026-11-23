"""التنبيهات: الطرفية دائماً، وتيليجرام اختيارياً (TELEGRAM_BOT_TOKEN و TELEGRAM_CHAT_ID)."""
from __future__ import annotations

import logging
import os
import re

from . import net

log = logging.getLogger(__name__)


class Notifier:
    def __init__(self, telegram: bool = True):
        self.token = os.environ.get("TELEGRAM_BOT_TOKEN")
        self.chat = os.environ.get("TELEGRAM_CHAT_ID")
        self.telegram = telegram and bool(self.token and self.chat)
        if self.telegram and not (re.fullmatch(r"\d+:[\w-]+", self.token) and re.fullmatch(r"-?\d+", self.chat)):
            log.warning("إعدادات تيليجرام غير صحيحة (الرمز يجب أن يكون مثل 123456:ABC... والرقم أرقاماً فقط) "
                        "— تم تعطيل تيليجرام. للإلغاء: unset TELEGRAM_BOT_TOKEN TELEGRAM_CHAT_ID")
            self.telegram = False

    def send_telegram(self, text: str) -> None:
        """يرسل إلى تيليجرام ويرفع الخطأ إن فشل. عند 429 (طلبات كثيرة) ينتظر المدة المطلوبة ويعيد."""
        import json
        import time
        import urllib.error
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        for attempt in range(2):
            try:
                net.post_form(url, {"chat_id": self.chat, "text": text})
                return
            except urllib.error.HTTPError as e:
                if e.code != 429 or attempt == 1:
                    raise
                try:
                    wait = int(json.loads(e.read().decode())["parameters"]["retry_after"])
                except Exception:
                    wait = 30
                log.info("تيليجرام يطلب الانتظار %s ثانية…", wait)
                time.sleep(min(wait, 120) + 1)

    def send(self, text: str) -> None:
        print(text, flush=True)
        if self.telegram:
            try:
                self.send_telegram(text)
            except Exception as e:
                log.warning("فشل إرسال تيليجرام: %s", e)
