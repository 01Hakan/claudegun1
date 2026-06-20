"""
Strategy Katmanı — Teknik İndikatörler
======================================

Saf Python ile yazılmış, harici bağımlılık (numpy/pandas) gerektirmeyen
indikatör fonksiyonları. Her fonksiyon bir fiyat/mum listesi alır ve giriş
ile aynı uzunlukta bir sonuç listesi döndürür. Hesaplanamayan baştaki
değerler ``None`` ile doldurulur (warm-up dönemi).

İçerik: SMA, EMA, RSI, MACD, ATR.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple


def sma(values: Sequence[float], period: int) -> List[Optional[float]]:
    """Basit Hareketli Ortalama (Simple Moving Average).

    İlk ``period-1`` eleman None döner.
    """
    if period <= 0:
        raise ValueError("period > 0 olmalı")
    out: List[Optional[float]] = [None] * len(values)
    running = 0.0
    for i, v in enumerate(values):
        running += v
        if i >= period:
            running -= values[i - period]
        if i >= period - 1:
            out[i] = running / period
    return out


def ema(values: Sequence[float], period: int) -> List[Optional[float]]:
    """Üssel Hareketli Ortalama (Exponential Moving Average).

    İlk değer, ilk ``period`` elemanın SMA'sı ile başlatılır (standart yaklaşım).
    """
    if period <= 0:
        raise ValueError("period > 0 olmalı")
    out: List[Optional[float]] = [None] * len(values)
    if len(values) < period:
        return out
    k = 2.0 / (period + 1.0)
    # Çekirdek (seed) = ilk period elemanın ortalaması.
    seed = sum(values[:period]) / period
    out[period - 1] = seed
    prev = seed
    for i in range(period, len(values)):
        prev = values[i] * k + prev * (1.0 - k)
        out[i] = prev
    return out


def rsi(values: Sequence[float], period: int = 14) -> List[Optional[float]]:
    """Göreli Güç Endeksi (Relative Strength Index), Wilder yumuşatması.

    0–100 arası değer döndürür. İlk ``period`` eleman None'dır.
    """
    if period <= 0:
        raise ValueError("period > 0 olmalı")
    out: List[Optional[float]] = [None] * len(values)
    if len(values) <= period:
        return out

    # İlk ortalama kazanç/kayıp.
    gains = 0.0
    losses = 0.0
    for i in range(1, period + 1):
        change = values[i] - values[i - 1]
        if change >= 0:
            gains += change
        else:
            losses -= change
    avg_gain = gains / period
    avg_loss = losses / period
    out[period] = _rsi_from(avg_gain, avg_loss)

    # Wilder yumuşatması ile devam.
    for i in range(period + 1, len(values)):
        change = values[i] - values[i - 1]
        gain = change if change > 0 else 0.0
        loss = -change if change < 0 else 0.0
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        out[i] = _rsi_from(avg_gain, avg_loss)
    return out


def _rsi_from(avg_gain: float, avg_loss: float) -> float:
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def macd(values: Sequence[float], fast: int = 12, slow: int = 26,
         signal: int = 9) -> Tuple[List[Optional[float]],
                                   List[Optional[float]],
                                   List[Optional[float]]]:
    """MACD = EMA(fast) - EMA(slow); Signal = EMA(MACD, signal).

    Returns:
        (macd_line, signal_line, histogram) — üçü de giriş uzunluğunda.
    """
    ema_fast = ema(values, fast)
    ema_slow = ema(values, slow)
    macd_line: List[Optional[float]] = [
        (f - s) if (f is not None and s is not None) else None
        for f, s in zip(ema_fast, ema_slow)
    ]
    # Signal hattı, MACD'nin None olmayan kısmının EMA'sı; indekslere geri haritalanır.
    valid = [(i, v) for i, v in enumerate(macd_line) if v is not None]
    signal_line: List[Optional[float]] = [None] * len(values)
    histogram: List[Optional[float]] = [None] * len(values)
    if len(valid) >= signal:
        sig_vals = ema([v for _, v in valid], signal)
        for (idx, _), sig in zip(valid, sig_vals):
            signal_line[idx] = sig
        for i in range(len(values)):
            if macd_line[i] is not None and signal_line[i] is not None:
                histogram[i] = macd_line[i] - signal_line[i]
    return macd_line, signal_line, histogram


def atr(highs: Sequence[float], lows: Sequence[float],
        closes: Sequence[float], period: int = 14) -> List[Optional[float]]:
    """Average True Range — volatilite ölçümü (Wilder yumuşatması).

    True Range = max(high-low, |high-prev_close|, |low-prev_close|).
    """
    n = len(closes)
    if not (len(highs) == len(lows) == n):
        raise ValueError("highs/lows/closes uzunlukları eşit olmalı")
    out: List[Optional[float]] = [None] * n
    if n <= period:
        return out

    true_ranges: List[float] = [0.0] * n
    for i in range(1, n):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        true_ranges[i] = tr

    # İlk ATR = ilk `period` TR'nin ortalaması (indeks 1..period).
    first = sum(true_ranges[1:period + 1]) / period
    out[period] = first
    prev = first
    for i in range(period + 1, n):
        prev = (prev * (period - 1) + true_ranges[i]) / period
        out[i] = prev
    return out
