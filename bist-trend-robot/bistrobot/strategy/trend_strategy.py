"""
Strategy Katmanı — 1 Saatlik Trend Stratejisi
=============================================

Çoklu indikatör (EMA / RSI / MACD / ATR) tabanlı kısa vadeli trend takip
stratejisi.

KARAR MANTIĞI
-------------
Trend yönü:
    EMA(slow) eğimi ve EMA(fast) > EMA(slow) ilişkisi ile belirlenir.
    - EMA(fast) > EMA(slow)  → YÜKSELİŞ trendi
    - EMA(fast) < EMA(slow)  → DÜŞÜŞ trendi

Giriş (BUY / long):
    - Yükseliş trendinde,
    - Fiyat (kapanış) kısa EMA'nın ÜZERİNE çıkmışken (taze kırılım),
    - RSI, [rsi_lower, rsi_upper] bandında (aşırı alım/satım dışı),
    - MACD histogramı pozitif (momentum teyidi).

Çıkış / SELL:
    - Düşüş trendine geçildiğinde veya fiyat kısa EMA'nın altına indiğinde.
    - (allow_short=True ise SELL aynı zamanda short giriş anlamına gelebilir;
       BIST'te açığa satış kısıtlı olduğundan varsayılan kapalıdır.)

Risk seviyeleri (sinyalle birlikte önerilir):
    - Stop-loss  = giriş - atr_stop_mult * ATR        (long)
    - Take-profit= giriş + risk_reward * (giriş - stop) (1:risk_reward)

NOT: Bu strateji EĞİTİM amaçlıdır; kâr garantisi yoktur.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from bistrobot.data.provider import Candle
from bistrobot.logging_utils.logger import get_logger
from bistrobot.strategy import indicators as ind
from bistrobot.strategy.base import Signal, SignalType, Strategy

log = get_logger("strategy.trend")


@dataclass
class TrendParams:
    """Trend stratejisi parametreleri (config'ten doldurulur)."""
    ema_fast: int = 12
    ema_slow: int = 26
    rsi_period: int = 14
    rsi_lower: float = 30.0
    rsi_upper: float = 70.0
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    atr_period: int = 14
    atr_stop_mult: float = 1.5
    risk_reward: float = 2.0
    allow_short: bool = False

    @classmethod
    def from_config(cls, strategy_cfg: dict) -> "TrendParams":
        """Config 'strategy' bölümünden parametre nesnesi üretir."""
        return cls(
            ema_fast=int(strategy_cfg.get("ema_fast", 12)),
            ema_slow=int(strategy_cfg.get("ema_slow", 26)),
            rsi_period=int(strategy_cfg.get("rsi_period", 14)),
            rsi_lower=float(strategy_cfg.get("rsi_lower", 30.0)),
            rsi_upper=float(strategy_cfg.get("rsi_upper", 70.0)),
            macd_fast=int(strategy_cfg.get("macd_fast", 12)),
            macd_slow=int(strategy_cfg.get("macd_slow", 26)),
            macd_signal=int(strategy_cfg.get("macd_signal", 9)),
            atr_period=int(strategy_cfg.get("atr_period", 14)),
            atr_stop_mult=float(strategy_cfg.get("atr_stop_mult", 1.5)),
            risk_reward=float(strategy_cfg.get("risk_reward", 2.0)),
            allow_short=bool(strategy_cfg.get("allow_short", False)),
        )


class TrendStrategy(Strategy):
    """EMA/RSI/MACD/ATR tabanlı 1 saatlik trend takip stratejisi."""

    def __init__(self, params: TrendParams) -> None:
        self.p = params

    @property
    def min_candles(self) -> int:
        # En uzun indikatör penceresi + makul tampon (warm-up).
        return max(self.p.ema_slow, self.p.macd_slow + self.p.macd_signal,
                   self.p.atr_period, self.p.rsi_period) + 5

    def generate_signal(self, candles: List[Candle]) -> Signal:
        symbol = candles[-1].symbol if candles else ""
        if len(candles) < self.min_candles:
            return Signal(symbol, SignalType.HOLD, price=candles[-1].close if candles else 0.0,
                          reason=f"Yetersiz veri ({len(candles)}/{self.min_candles})")

        closes = [c.close for c in candles]
        highs = [c.high for c in candles]
        lows = [c.low for c in candles]

        ema_fast = ind.ema(closes, self.p.ema_fast)
        ema_slow = ind.ema(closes, self.p.ema_slow)
        rsi_vals = ind.rsi(closes, self.p.rsi_period)
        _, _, macd_hist = ind.macd(closes, self.p.macd_fast,
                                   self.p.macd_slow, self.p.macd_signal)
        atr_vals = ind.atr(highs, lows, closes, self.p.atr_period)

        # En güncel ve bir önceki bar değerleri.
        i = len(closes) - 1
        price = closes[i]
        ef, es = ema_fast[i], ema_slow[i]
        rsi_now = rsi_vals[i]
        hist = macd_hist[i]
        atr_now = atr_vals[i]
        prev_close = closes[i - 1]
        prev_ef = ema_fast[i - 1]

        # Herhangi bir indikatör hazır değilse (warm-up) HOLD.
        if None in (ef, es, rsi_now, hist, atr_now, prev_ef):
            return Signal(symbol, SignalType.HOLD, price,
                          reason="İndikatörler henüz hazır değil")

        snapshot = {
            "price": round(price, 4), "ema_fast": round(ef, 4),
            "ema_slow": round(es, 4), "rsi": round(rsi_now, 2),
            "macd_hist": round(hist, 4), "atr": round(atr_now, 4),
        }

        uptrend = ef > es
        downtrend = ef < es
        # "Taze" kırılım: önceki barda fiyat kısa EMA altında, şimdi üstünde.
        crossed_up = prev_close <= prev_ef and price > ef
        crossed_down = prev_close >= prev_ef and price < ef
        rsi_ok = self.p.rsi_lower <= rsi_now <= self.p.rsi_upper

        # --- BUY (long giriş) ---
        if uptrend and (crossed_up or price > ef) and rsi_ok and hist > 0:
            stop = price - self.p.atr_stop_mult * atr_now
            risk = price - stop
            take = price + self.p.risk_reward * risk
            reason = (f"Yükseliş trendi (EMA{self.p.ema_fast}>{self.p.ema_slow}), "
                      f"fiyat kısa EMA üstü, RSI={rsi_now:.1f} bantta, "
                      f"MACD hist>0 → LONG")
            log.info("[%s] BUY | %s", symbol, reason)
            return Signal(symbol, SignalType.BUY, price, round(stop, 4),
                          round(take, 4), reason, snapshot)

        # --- SELL (çıkış / opsiyonel short) ---
        if downtrend or crossed_down:
            reason = (f"Düşüş trendi/kısa EMA altı kırılım "
                      f"(EMA{self.p.ema_fast}<{self.p.ema_slow}) → ÇIKIŞ/SELL")
            log.info("[%s] SELL | %s", symbol, reason)
            stop = take = None
            if self.p.allow_short:
                stop = price + self.p.atr_stop_mult * atr_now
                take = price - self.p.risk_reward * (stop - price)
                stop, take = round(stop, 4), round(take, 4)
            return Signal(symbol, SignalType.SELL, price, stop, take,
                          reason, snapshot)

        # --- HOLD ---
        return Signal(symbol, SignalType.HOLD, price,
                      reason="Net sinyal yok (trend/momentum teyidi eksik)",
                      indicators=snapshot)
