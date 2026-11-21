"""رسم بياني للسعر مع مناطق العرض/الطلب والإشارة الحالية، وتقرير نصي."""

import os

import pandas as pd

from bot.signals import Signal
from bot.zones import Zone


def plot_chart(df: pd.DataFrame, zones: list[Zone], symbol: str, signal: Signal | None, out_path: str) -> str:
    """يرسم الرسم البياني ويحفظه. يرفع ImportError إن كانت matplotlib غير مثبتة
    (مثلاً على بيئات محدودة كـ Termux/Android)، ليتعامل المستدعي مع ذلك بإعلام
    المستخدم بدل انهيار البرنامج بالكامل."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(14, 7))

    ax.plot(df.index, df["close"], color="#2962ff", linewidth=1.2, label="Close")
    if "ema_50" in df:
        ax.plot(df.index, df["ema_50"], color="#ff9800", linewidth=1, label="EMA 50")
    if "ema_200" in df:
        ax.plot(df.index, df["ema_200"], color="#9c27b0", linewidth=1, label="EMA 200")

    for zone in zones:
        color = "#26a69a" if zone.kind == "demand" else "#ef5350"
        alpha = 0.15 + min(zone.touches, 5) * 0.05
        ax.axhspan(zone.low, zone.high, color=color, alpha=alpha)

    if signal:
        marker = "^" if signal.side == "buy" else "v"
        color = "#26a69a" if signal.side == "buy" else "#ef5350"
        ax.scatter([df.index[-1]], [signal.price], marker=marker, s=160, color=color, zorder=5, label=f"{signal.side.upper()} signal")
        ax.axhline(signal.stop_loss, color="#ef5350", linestyle="--", linewidth=0.8, label="Stop loss")
        ax.axhline(signal.take_profit, color="#26a69a", linestyle="--", linewidth=0.8, label="Take profit")

    ax.set_title(f"{symbol} — Demand (green) / Supply (red) zones")
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(alpha=0.2)
    fig.tight_layout()

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def text_report(symbol: str, timeframe: str, zones: list[Zone], signal: Signal | None, price: float) -> str:
    lines = [
        f"تقرير تحليل السوق — {symbol} ({timeframe})",
        f"السعر الحالي: {price:.6f}",
        "",
        "مناطق الطلب (دعم محتمل للشراء):",
    ]
    demand = sorted([z for z in zones if z.kind == "demand"], key=lambda z: -z.mid)
    supply = sorted([z for z in zones if z.kind == "supply"], key=lambda z: z.mid)

    if demand:
        for z in demand:
            lines.append(f"  - {z.low:.6f} إلى {z.high:.6f}  (قوة: {z.touches} ارتدادات)")
    else:
        lines.append("  - لم تُكتشف مناطق طلب واضحة في هذه الفترة.")

    lines.append("")
    lines.append("مناطق العرض (مقاومة محتملة للبيع):")
    if supply:
        for z in supply:
            lines.append(f"  - {z.low:.6f} إلى {z.high:.6f}  (قوة: {z.touches} ارتدادات)")
    else:
        lines.append("  - لم تُكتشف مناطق عرض واضحة في هذه الفترة.")

    lines.append("")
    if signal:
        lines.append(f"الإشارة الحالية: {signal.side.upper()}")
        lines.append(f"  سعر الدخول: {signal.price:.6f}")
        lines.append(f"  وقف الخسارة: {signal.stop_loss:.6f}")
        lines.append(f"  الهدف: {signal.take_profit:.6f}")
        lines.append(f"  نسبة المكافأة/الخطر: {signal.reward_risk_ratio:.2f}")
        lines.append(f"  السبب: {signal.reason}")
    else:
        lines.append("الإشارة الحالية: لا توجد إشارة شراء/بيع مؤكدة الآن — السعر ليس عند منطقة واضحة بما يكفي.")

    return "\n".join(lines)
