"""إشعار اختياري على الهاتف عبر Termux:API عند حدوث إشارة أو صفقة.

يعمل فقط إذا كان أمر termux-notification متوفراً (حزمة termux-api مثبتة +
تطبيق Termux:API المرافق). في أي بيئة أخرى (خادم VPS مثلاً) يتجاهل الإشعار
بصمت دون أي خطأ."""

import shutil
import subprocess


def notify(title: str, content: str) -> None:
    if shutil.which("termux-notification") is None:
        return
    try:
        subprocess.run(
            ["termux-notification", "--title", title, "--content", content],
            check=False,
            timeout=5,
        )
    except Exception:
        pass
