"""
Strategy Katmanı — Temel Arayüz ve Sinyal Modeli
================================================

Tüm stratejiler ``Strategy`` arayüzünü uygular ve ``Signal`` üretir. Bu
sayede yeni stratejiler (momentum, breakout, mean-reversion vb.) aynı
çalışma döngüsüne sorunsuz takılabilir.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from bistrobot.data.provider import Candle


class SignalType(str, Enum):
    """Strateji çıktısı sinyal türü."""
    BUY = "BUY"          # Long pozisyon aç
    SELL = "SELL"        # Pozisyon kapat / (izinliyse) short aç
    HOLD = "HOLD"        # İşlem yok


@dataclass
class Signal:
    """Strateji tarafından üretilen tek bir sinyal.

    Attributes:
        symbol: BIST sembolü.
        type: BUY / SELL / HOLD.
        price: Sinyal anındaki referans fiyat (son kapanış).
        stop_loss: Önerilen stop-loss fiyatı (None olabilir).
        take_profit: Önerilen take-profit fiyatı (None olabilir).
        reason: Kararın insan-okunur açıklaması (loglama/izlenebilirlik).
        indicators: Karara esas indikatör değerleri (denetim/iz için).
    """
    symbol: str
    type: SignalType
    price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    reason: str = ""
    indicators: Dict[str, float] = field(default_factory=dict)


class Strategy(abc.ABC):
    """Soyut strateji arayüzü."""

    @abc.abstractmethod
    def generate_signal(self, candles: List[Candle]) -> Signal:
        """Verilen (kronolojik) mum dizisi için bir sinyal üretir.

        Son eleman en güncel TAMAMLANMIŞ mumdur. Yetersiz veri varsa
        HOLD döndürülmelidir.
        """
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def min_candles(self) -> int:
        """Sinyal üretmek için gereken minimum mum sayısı (warm-up)."""
        raise NotImplementedError
