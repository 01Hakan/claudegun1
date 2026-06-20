"""
Data Katmanı — Mock / Sentetik Veri Sağlayıcı
=============================================

``IDataProvider`` arayüzünün, gerçek API olmadan geliştirme/backtest/paper
trading için kullanılan sentetik implementasyonu.

Üretilen seri: trend + dalgalanma + rastgele gürültü içeren gerçekçi bir
geometrik fiyat süreci (deterministik tohum ile tekrarlanabilir).

# >>> GERÇEK API ENTEGRASYON NOKTASI:
#     Gerçek piyasada bu sınıf yerine, aracı kurumun REST/WebSocket
#     uçlarından OHLCV çeken bir "BrokerDataProvider" yazın ve aynı
#     IDataProvider arayüzünü uygulayın.
"""

from __future__ import annotations

import math
import random
from datetime import datetime, timedelta
from typing import Dict, List

from bistrobot.data.provider import Candle, IDataProvider
from bistrobot.logging_utils.logger import get_logger

log = get_logger("data.mock")

# Timeframe -> dakika eşlemesi.
_TIMEFRAME_MINUTES = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "1d": 1440}


def timeframe_minutes(timeframe: str) -> int:
    """Zaman dilimi string'ini dakikaya çevirir."""
    if timeframe not in _TIMEFRAME_MINUTES:
        raise ValueError(f"Desteklenmeyen timeframe: {timeframe}")
    return _TIMEFRAME_MINUTES[timeframe]


class MockDataProvider(IDataProvider):
    """Sentetik OHLCV üreten veri sağlayıcı.

    Args:
        seed: Tekrarlanabilirlik için rastgelelik tohumu.
        start_price: Başlangıç fiyatı.
        bars: Önceden üretilecek mum sayısı (geçmiş havuzu).
        trend_per_bar: Mum başına ortalama getiri (pozitif=yükseliş eğilimi).
        volatility: Mum başına oynaklık (std sapma yaklaşık değeri).
    """

    def __init__(self, seed: int = 42, start_price: float = 100.0,
                 bars: int = 1500, trend_per_bar: float = 0.0005,
                 volatility: float = 0.012) -> None:
        self._seed = seed
        self._start_price = start_price
        self._bars = bars
        self._trend = trend_per_bar
        self._vol = volatility
        # Sembol başına önceden üretilmiş mum havuzu ve "canlı" imleç.
        self._series: Dict[str, List[Candle]] = {}
        self._cursor: Dict[str, int] = {}

    # ----- Yardımcı: bir sembol için seri üret -----------------------------
    def _ensure_series(self, symbol: str, timeframe: str) -> List[Candle]:
        if symbol in self._series:
            return self._series[symbol]

        rng = random.Random(f"{self._seed}:{symbol}")
        minutes = timeframe_minutes(timeframe)
        # Geçmişe doğru başlangıç zamanı.
        t = datetime(2024, 1, 1, 10, 0, 0)
        price = self._start_price
        candles: List[Candle] = []

        for i in range(self._bars):
            # Rejim değişimi: trend yönü periyodik olarak salınır (gerçekçilik).
            regime = math.sin(i / 120.0)  # -1..1 arası yavaş salınım
            drift = self._trend * (1.0 + regime)
            shock = rng.gauss(0.0, self._vol)
            ret = drift + shock
            open_p = price
            close_p = max(0.01, open_p * (1.0 + ret))
            # High/Low: intrabar oynaklık.
            spread = abs(rng.gauss(0.0, self._vol)) * open_p
            high_p = max(open_p, close_p) + spread
            low_p = max(0.01, min(open_p, close_p) - spread)
            volume = abs(rng.gauss(1_000_000, 250_000))

            candles.append(Candle(
                timestamp=t, open=round(open_p, 2), high=round(high_p, 2),
                low=round(low_p, 2), close=round(close_p, 2),
                volume=round(volume, 0), symbol=symbol,
            ))
            price = close_p
            t = t + timedelta(minutes=minutes)

        self._series[symbol] = candles
        # Canlı imleç: warm-up için serinin %70'inden başlat.
        self._cursor[symbol] = int(self._bars * 0.7)
        log.debug("Sentetik seri üretildi: %s (%d mum)", symbol, len(candles))
        return candles

    # ----- IDataProvider implementasyonu -----------------------------------
    def get_historical_candles(self, symbol: str, timeframe: str,
                               limit: int) -> List[Candle]:
        series = self._ensure_series(symbol, timeframe)
        # Backtest, tüm geçmişi (imlece kadar) ister; en yeni `limit` mum.
        upto = self._cursor.get(symbol, len(series))
        window = series[:upto]
        return window[-limit:] if limit < len(window) else window

    def get_latest_candle(self, symbol: str, timeframe: str) -> Candle:
        """Canlı akışı taklit eder: her çağrıda imleci bir mum ilerletir."""
        series = self._ensure_series(symbol, timeframe)
        idx = self._cursor.get(symbol, 0)
        if idx >= len(series):
            # Seri bitti — son mumu tekrar döndür (gerçek API'de yeni mum beklenir).
            return series[-1]
        candle = series[idx]
        self._cursor[symbol] = idx + 1
        return candle

    # ----- Backtest yardımcısı --------------------------------------------
    def full_series(self, symbol: str, timeframe: str) -> List[Candle]:
        """Backtest motoru için sembolün TÜM mumlarını döndürür."""
        return list(self._ensure_series(symbol, timeframe))
