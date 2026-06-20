"""
Data Katmanı — Arayüzler ve Modeller
====================================

Piyasa verisi alımı için soyut ``IDataProvider`` arayüzü ile ortak ``Candle``
(mum/OHLCV) veri modeli.

Farklı bir veri kaynağı (aracı kurum REST/WebSocket, üçüncü parti veri
sağlayıcı vb.) entegre etmek için yalnızca ``IDataProvider`` arayüzünü
uygulayan yeni bir sınıf yazmanız yeterlidir; strateji ve döngü kodu
değişmez.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
from datetime import datetime
from typing import List


@dataclass(frozen=True)
class Candle:
    """Tek bir OHLCV mumu (kapanmış/tamamlanmış).

    Attributes:
        timestamp: Mumun açılış zamanı.
        open, high, low, close: Fiyatlar.
        volume: Hacim.
        symbol: BIST sembolü (ör. "AKBNK.E").
    """
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    symbol: str = ""


class IDataProvider(abc.ABC):
    """Piyasa verisi sağlayıcı soyut arayüzü.

    Strateji katmanı yalnızca bu arayüze bağımlıdır; somut sağlayıcılar
    (mock, gerçek API) bu sözleşmeyi uygular.
    """

    @abc.abstractmethod
    def get_historical_candles(self, symbol: str, timeframe: str,
                               limit: int) -> List[Candle]:
        """Geçmiş (tamamlanmış) mumları döndürür — backtest ve indikatör
        ısınması (warm-up) için.

        Args:
            symbol: BIST sembolü.
            timeframe: "1m", "5m", "1h" gibi.
            limit: İstenen mum sayısı (en yeniler).
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_latest_candle(self, symbol: str, timeframe: str) -> Candle:
        """En son TAMAMLANMIŞ mumu döndürür (canlı/paper döngü için).

        Gerçek implementasyonda yalnızca kapanmış mumu döndürdüğünüzden
        emin olun; oluşmakta olan (yarım) mum sinyal üretmemelidir.
        """
        raise NotImplementedError

    def is_market_open(self, now: datetime) -> bool:
        """Piyasanın açık olup olmadığını döndürür.

        Varsayılan: BIST pay piyasası seansı (TSİ 10:00–18:00, hafta içi).
        Gerçek implementasyonda resmi tatiller de dikkate alınmalıdır.
        """
        if now.weekday() >= 5:  # Cumartesi(5)/Pazar(6)
            return False
        return 10 <= now.hour < 18
