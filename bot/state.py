"""تتبّع حالة الصفقة المفتوحة عبر دورات التشغيل المتكررة (ملف JSON محلي).

ضروري لأي تشغيل مستمر/تلقائي: بدون هذا، كل دورة تحلّل السوق من الصفر ولا
تعرف أن صفقة سابقة لا تزال مفتوحة، فقد تفتح صفقات حقيقية مكررة لنفس الإشارة."""

import json
import os
from dataclasses import asdict, dataclass


@dataclass
class OpenPosition:
    symbol: str
    side: str  # "buy" أو "sell"
    entry_price: float
    stop_loss: float
    take_profit: float
    quantity: float
    opened_at: str
    # هل فُتحت هذه الصفقة فعلياً على المنصة (live=True) أم أنها محاكاة فقط
    # (dry-run)؟ ضروري لمنع جلسة live لاحقة من معاملة صفقة محاكاة كصفقة
    # حقيقية وإرسال أمر إغلاق حقيقي بأموال حقيقية لصفقة لم تُفتح أصلاً.
    # افتراضي False للتوافق مع ملفات حالة قديمة أُنشئت قبل إضافة هذا الحقل.
    live: bool = False
    # معرّف أمر الحماية (وقف خسارة/هدف OCO) الخاص بهذه الصفقة تحديداً على
    # المنصة، إن نجح وضعه. يُستخدم عند الإغلاق لإلغاء هذا الأمر بالذات فقط،
    # دون المساس بأي أوامر أخرى غير متعلقة بالبوت قد يضعها المستخدم يدوياً
    # على نفس الرمز. None إن لم يُوضع أمر حماية أصلاً (فشل OCO أو غير مدعوم).
    protective_order_id: str | None = None
    protective_order_list_id: str | None = None


def load_open_position(state_path: str) -> OpenPosition | None:
    if not os.path.exists(state_path):
        return None
    with open(state_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not data:
        return None
    return OpenPosition(**data)


def save_open_position(state_path: str, position: OpenPosition) -> None:
    os.makedirs(os.path.dirname(state_path) or ".", exist_ok=True)
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(asdict(position), f, ensure_ascii=False, indent=2)


def clear_open_position(state_path: str) -> None:
    if os.path.exists(state_path):
        os.remove(state_path)
