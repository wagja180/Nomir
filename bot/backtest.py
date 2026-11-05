"""تنفيذ تجريبي تاريخي (backtest) لاستراتيجية مناطق العرض/الطلب.

يُعاد حساب المناطق والمؤشرات تدريجياً شمعة بشمعة (بدون معرفة المستقبل) لمحاكاة
كيفية تصرف البوت تاريخياً، ثم تُجمع نتائج كل صفقة مغلقة لحساب الأداء.
"""

from dataclasses import dataclass

import pandas as pd

from bot.indicators import add_indicators
from bot.signals import Signal, generate_signal
from bot.zones import detect_zones


@dataclass
class Trade:
    side: str
    entry_price: float
    stop_loss: float
    take_profit: float
    exit_price: float
    exit_reason: str
    pnl_pct: float


@dataclass
class BacktestResult:
    trades: list[Trade]

    @property
    def win_rate(self) -> float:
        if not self.trades:
            return 0.0
        wins = sum(1 for t in self.trades if t.pnl_pct > 0)
        return wins / len(self.trades)

    @property
    def total_return_pct(self) -> float:
        total = 1.0
        for t in self.trades:
            total *= 1 + t.pnl_pct
        return (total - 1) * 100

    def summary(self) -> str:
        n = len(self.trades)
        if n == 0:
            return "لم تُنفذ أي صفقة خلال فترة الاختبار."
        avg = sum(t.pnl_pct for t in self.trades) / n * 100
        return (
            f"عدد الصفقات: {n} | نسبة الفوز: {self.win_rate * 100:.1f}% | "
            f"متوسط العائد لكل صفقة: {avg:.2f}% | العائد الإجمالي المركّب: {self.total_return_pct:.2f}%"
        )


def run_backtest(df: pd.DataFrame, min_history: int = 210, step_recompute_zones: int = 10) -> BacktestResult:
    """df: بيانات OHLCV كاملة مرتبة تصاعدياً بالزمن.

    step_recompute_zones: كل كم شمعة تُعاد حساب المناطق (لتسريع الاختبار؛ إعادة
    الحساب كل شمعة مكلفة حسابياً وغير ضرورية لأن المناطق تتغير بشكل بطيء).
    """
    full = add_indicators(df)
    trades: list[Trade] = []

    open_trade: Signal | None = None
    zones = []

    for i in range(min_history, len(full)):
        window = full.iloc[: i + 1]

        if i % step_recompute_zones == 0 or not zones:
            zones = detect_zones(window.iloc[:-1])  # مناطق محسوبة من الماضي فقط، بدون الشمعة الحالية

        current = window.iloc[-1]

        if open_trade is None:
            sig = generate_signal(window, zones)
            if sig:
                open_trade = sig
            continue

        price = float(current["close"])
        high = float(current["high"])
        low = float(current["low"])

        hit_stop = (open_trade.side == "buy" and low <= open_trade.stop_loss) or (
            open_trade.side == "sell" and high >= open_trade.stop_loss
        )
        hit_target = (open_trade.side == "buy" and high >= open_trade.take_profit) or (
            open_trade.side == "sell" and low <= open_trade.take_profit
        )

        if hit_stop or hit_target:
            exit_price = open_trade.stop_loss if hit_stop else open_trade.take_profit
            if open_trade.side == "buy":
                pnl_pct = (exit_price - open_trade.price) / open_trade.price
            else:
                pnl_pct = (open_trade.price - exit_price) / open_trade.price

            trades.append(
                Trade(
                    side=open_trade.side,
                    entry_price=open_trade.price,
                    stop_loss=open_trade.stop_loss,
                    take_profit=open_trade.take_profit,
                    exit_price=exit_price,
                    exit_reason="stop_loss" if hit_stop else "take_profit",
                    pnl_pct=pnl_pct,
                )
            )
            open_trade = None

    return BacktestResult(trades=trades)
