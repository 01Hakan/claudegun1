"""
Execution Katmanı — Arayüzler ve Modeller
=========================================

Aracı kuruma emir gönderme/iptal/sorgulama için soyut ``IOrderExecutor``
arayüzü ile ``Order`` ve ``Position`` veri modelleri.

Gerçek aracı kurum entegrasyonu için bu arayüzü uygulayan yeni bir sınıf
(ör. ``BrokerOrderExecutor``) yazıp ``cmd/main.py`` fabrikasına bağlamanız
yeterlidir.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class PriceType(str, Enum):
    MARKET = "MARKET"   # Piyasa emri
    LIMIT = "LIMIT"     # Limit emri (price gerekir)


class OrderStatus(str, Enum):
    NEW = "NEW"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


@dataclass
class Order:
    """Bir emir kaydı."""
    order_id: str
    symbol: str
    side: OrderSide
    quantity: int
    price_type: PriceType
    price: Optional[float] = None          # LIMIT için gerekli
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    status: OrderStatus = OrderStatus.NEW
    filled_price: Optional[float] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Position:
    """Açık bir pozisyon."""
    symbol: str
    side: OrderSide
    quantity: int
    entry_price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    opened_at: datetime = field(default_factory=datetime.utcnow)

    def unrealized_pnl(self, current_price: float) -> float:
        """Cari fiyata göre gerçekleşmemiş kâr/zarar (TRY)."""
        direction = 1 if self.side == OrderSide.BUY else -1
        return (current_price - self.entry_price) * self.quantity * direction


class IOrderExecutor(abc.ABC):
    """Emir yürütme soyut arayüzü."""

    @abc.abstractmethod
    def create_order(self, symbol: str, side: OrderSide, quantity: int,
                     price_type: PriceType, price: Optional[float] = None,
                     stop_loss: Optional[float] = None,
                     take_profit: Optional[float] = None) -> Order:
        """Yeni emir oluşturur ve gönderir."""
        raise NotImplementedError

    @abc.abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Açık bir emri iptal eder. Başarılıysa True."""
        raise NotImplementedError

    @abc.abstractmethod
    def get_open_orders(self) -> List[Order]:
        """Bekleyen (NEW) emirleri döndürür."""
        raise NotImplementedError

    @abc.abstractmethod
    def get_positions(self) -> List[Position]:
        """Açık pozisyonları döndürür."""
        raise NotImplementedError
