"""طلبات HTTP بمكتبة Python القياسية فقط (بدون requests)."""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (forexbot)"


def request(url: str, params: dict | None = None, headers: dict | None = None,
            data: bytes | None = None, method: str | None = None, timeout: int = 20) -> str:
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    h = {"User-Agent": UA, **(headers or {})}
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def get_text(url: str, **kw) -> str:
    return request(url, **kw)


def get_json(url: str, **kw):
    return json.loads(request(url, **kw))


def post_json(url: str, body: dict, headers: dict | None = None, timeout: int = 20):
    h = {"Content-Type": "application/json", **(headers or {})}
    return json.loads(request(url, headers=h, data=json.dumps(body).encode(), method="POST", timeout=timeout))


def post_form(url: str, fields: dict, timeout: int = 15) -> str:
    return request(url, data=urllib.parse.urlencode(fields).encode(), method="POST", timeout=timeout)
