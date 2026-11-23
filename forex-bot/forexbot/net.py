"""طلبات HTTP بمكتبة Python القياسية فقط (بدون requests)."""
from __future__ import annotations

import http.client
import json
import time
import urllib.error
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (forexbot)"


def request(url: str, params: dict | None = None, headers: dict | None = None,
            data: bytes | None = None, method: str | None = None, timeout: int = 20) -> str:
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    h = {"User-Agent": UA, **(headers or {})}
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    # إعادة المحاولة عند انقطاع الاتصال (شائع على شبكات الجوال 4G)
    attempts = 1 if data is not None else 3
    for k in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", errors="replace")
        except (http.client.IncompleteRead, ConnectionError, TimeoutError, urllib.error.URLError) as e:
            if isinstance(e, urllib.error.HTTPError) or k == attempts - 1:
                raise
            time.sleep(2 * (k + 1))
    raise RuntimeError("unreachable")


def get_text(url: str, **kw) -> str:
    return request(url, **kw)


def get_json(url: str, **kw):
    return json.loads(request(url, **kw))


def post_json(url: str, body: dict, headers: dict | None = None, timeout: int = 20):
    h = {"Content-Type": "application/json", **(headers or {})}
    return json.loads(request(url, headers=h, data=json.dumps(body).encode(), method="POST", timeout=timeout))


def post_form(url: str, fields: dict, timeout: int = 30, retries: int = 3) -> str:
    """POST مع إعادة المحاولة عند انقطاع الشبكة أو انتهاء المهلة."""
    body = urllib.parse.urlencode(fields).encode()
    for k in range(retries):
        try:
            return request(url, data=body, method="POST", timeout=timeout)
        except urllib.error.HTTPError:
            raise  # خطأ من الخادم (مثل رمز خاطئ) — لا فائدة من التكرار
        except (OSError, http.client.HTTPException):
            if k == retries - 1:
                raise
            time.sleep(3 * (k + 1))
    raise RuntimeError("unreachable")
