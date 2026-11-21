"""التنفيذ: وسيط ورقي (محاكاة — الوضع الافتراضي) أو OANDA."""
from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

import requests

from . import symbols

log = logging.getLogger(__name__)


@dataclass
class Position:
    id: str
    symbol: str
    side: str
    units: int
    entry: float
    stop_loss: float
    take_profit: float
    opened_at: str
    closed_at: str | None = None
    exit: float | None = None
    pnl: float = 0.0
    reason: str = ""


def _pnl(p: Position, price: float, quote_to_account: float = 1.0) -> float:
    sgn = 1 if p.side == "BUY" else -1
    return sgn * (price - p.entry) * p.units * quote_to_account


class PaperBroker:
    """يحاكي التداول ويحفظ الحالة في ملف JSON."""

    def __init__(self, state_file: str = "paper_state.json", balance: float = 10000.0,
                 spread_pips: float = 1.0):
        self.state_file = state_file
        self.spread_pips = spread_pips
        self.balance = balance
        self.positions: list[Position] = []
        self.history: list[Position] = []
        self._load()

    # --- الحالة ---
    def _load(self):
        if os.path.exists(self.state_file):
            with open(self.state_file, encoding="utf-8") as f:
                s = json.load(f)
            self.balance = s["balance"]
            self.positions = [Position(**p) for p in s["positions"]]
            self.history = [Position(**p) for p in s["history"]]

    def _save(self):
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump({"balance": self.balance,
                       "positions": [asdict(p) for p in self.positions],
                       "history": [asdict(p) for p in self.history]}, f, ensure_ascii=False, indent=2)

    # --- الواجهة ---
    def open_positions(self) -> list[Position]:
        return list(self.positions)

    def day_pnl(self) -> float:
        today = datetime.now(timezone.utc).date().isoformat()
        return sum(p.pnl for p in self.history if (p.closed_at or "").startswith(today))

    def market_order(self, symbol: str, side: str, units: int, sl: float, tp: float,
                     price: float) -> Position:
        half = self.spread_pips * symbols.pip_size(symbol) / 2
        fill = price + half if side == "BUY" else price - half
        p = Position(id=f"P{len(self.history) + len(self.positions) + 1}", symbol=symbols.normalize(symbol),
                     side=side, units=units, entry=fill, stop_loss=sl, take_profit=tp,
                     opened_at=datetime.now(timezone.utc).isoformat())
        self.positions.append(p)
        self._save()
        return p

    def update(self, symbol: str, high: float, low: float, last: float,
               quote_to_account: float = 1.0) -> list[Position]:
        """يغلق الصفقات التي لمست الوقف أو الهدف. (عند لمس الاثنين نفترض الوقف — تحفّظاً)"""
        closed = []
        for p in list(self.positions):
            if p.symbol != symbols.normalize(symbol):
                continue
            hit_sl = low <= p.stop_loss if p.side == "BUY" else high >= p.stop_loss
            hit_tp = high >= p.take_profit if p.side == "BUY" else low <= p.take_profit
            if hit_sl or hit_tp:
                price = p.stop_loss if hit_sl else p.take_profit
                self._close(p, price, "وقف الخسارة" if hit_sl else "جني الربح", quote_to_account)
                closed.append(p)
        if closed:
            self._save()
        return closed

    def _close(self, p: Position, price: float, reason: str, q2a: float):
        p.exit, p.reason = price, reason
        p.pnl = _pnl(p, price, q2a)
        p.closed_at = datetime.now(timezone.utc).isoformat()
        self.balance += p.pnl
        self.positions.remove(p)
        self.history.append(p)


class OandaBroker:
    """تنفيذ فعلي عبر OANDA v20 (يُفضّل البدء بالحساب التجريبي practice)."""

    def __init__(self, practice: bool = True):
        self.token = os.environ["OANDA_TOKEN"]
        self.account = os.environ["OANDA_ACCOUNT_ID"]
        host = "api-fxpractice.oanda.com" if practice else "api-fxtrade.oanda.com"
        self.base = f"https://{host}/v3/accounts/{self.account}"
        self.s = requests.Session()
        self.s.headers.update({"Authorization": f"Bearer {self.token}",
                               "Content-Type": "application/json"})

    @property
    def balance(self) -> float:
        r = self.s.get(f"{self.base}/summary", timeout=20)
        r.raise_for_status()
        return float(r.json()["account"]["balance"])

    def open_positions(self) -> list[Position]:
        r = self.s.get(f"{self.base}/openTrades", timeout=20)
        r.raise_for_status()
        out = []
        for t in r.json()["trades"]:
            u = int(float(t["currentUnits"]))
            out.append(Position(id=t["id"], symbol=symbols.normalize(t["instrument"]),
                                side="BUY" if u > 0 else "SELL", units=abs(u),
                                entry=float(t["price"]),
                                stop_loss=float(t.get("stopLossOrder", {}).get("price", 0)),
                                take_profit=float(t.get("takeProfitOrder", {}).get("price", 0)),
                                opened_at=t["openTime"], pnl=float(t.get("unrealizedPL", 0))))
        return out

    def market_order(self, symbol: str, side: str, units: int, sl: float, tp: float,
                     price: float | None = None) -> dict:
        digits = 3 if symbols.split(symbol)[1] == "JPY" else 5
        body = {"order": {
            "type": "MARKET", "instrument": symbols.to_oanda(symbol),
            "units": str(units if side == "BUY" else -units), "timeInForce": "FOK",
            "stopLossOnFill": {"price": f"{sl:.{digits}f}"},
            "takeProfitOnFill": {"price": f"{tp:.{digits}f}"},
        }}
        r = self.s.post(f"{self.base}/orders", json=body, timeout=20)
        r.raise_for_status()
        return r.json()

    def update(self, *a, **k) -> list:
        return []  # OANDA تغلق الصفقات تلقائياً عند الوقف/الهدف
