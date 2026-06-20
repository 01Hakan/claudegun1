"""
Execution Katmanı — Mock (Simülasyon) Emir Yürütücü
===================================================

``IOrderExecutor`` arayüzünün, gerçek para KULLANMAYAN bellek-içi
simülasyon implementasyonu. Paper trading ve backtest için kullanılır.

Davranış:
  - Emirler bellekte tutulur; MARKET emirler anında dolar (fill).
  - Her fiyat güncellemesinde (``mark_price``) açık pozisyonların stop-loss /
    take-profit seviyeleri kontrol edilir; tetiklenen pozisyonlar kapatılır.
  - Komisyon, her dolan emirde nominal değer üzerinden düşülür.

# >>> GERÇEK API ENTEGRASYON NOKTASI:
#     create_order/cancel_order/get_* metodları içindeki simülasyon mantığını,
#     gerçek aracı kurumun HTTP/WebSocket çağrılarıyla değiştirin. Emir ID'leri
#     ve doluluk bilgisi gerçek API'den gelmelidir.
"""

from __future__ import annotations

import itertools
from datetime import datetime
from typing import Callable, Dict, List, Optional

from bistrobot.execution.executor import (
    IOrderExecutor, Order, OrderSide, OrderStatus, Position, PriceType,
)
from bistrobot.logging_utils.logger import get_logger

log = get_logger("execution.mock")


class MockOrderExecutor(IOrderExecutor):
    """Bellek-içi emir simülatörü (gerçek para yok).

    Args:
        commission_pct: İşlem başına komisyon yüzdesi.
        on_close: Pozisyon kapanınca çağrılan geri-çağrı (pnl iletmek için);
            RiskManager.register_close'a bağlanabilir.
    """

    def __init__(self, commission_pct: float = 0.0,
                 on_close: Optional[Callable[[float, datetime], None]] = None) -> None:
        self._commission = commission_pct / 100.0
        self._on_close = on_close
        self._orders: Dict[str, Order] = {}
        self._positions: Dict[str, Position] = {}     # symbol -> Position
        self._ids = itertools.count(1)
        self.realized_pnl = 0.0
        self.commission_paid = 0.0
        self.closed_trades: List[dict] = []           # Backtest istatistiği için
        # Simülasyon "şimdi"si — mark_price ile güncellenir; kapanış geri-çağrısına
        # bar zamanı taşımak için (backtest'te günlük takip doğru olsun diye).
        self._now: Optional[datetime] = None

    # ----- IOrderExecutor --------------------------------------------------
    def create_order(self, symbol: str, side: OrderSide, quantity: int,
                     price_type: PriceType, price: Optional[float] = None,
                     stop_loss: Optional[float] = None,
                     take_profit: Optional[float] = None) -> Order:
        oid = f"MOCK-{next(self._ids):06d}"
        order = Order(oid, symbol, side, quantity, price_type, price,
                      stop_loss, take_profit)

        if quantity <= 0:
            order.status = OrderStatus.REJECTED
            log.warning("Emir reddedildi (adet<=0): %s", oid)
            self._orders[oid] = order
            return order

        # MARKET emir: girişte verilen referans fiyattan anında dolar.
        # LIMIT emir gerçek API'de beklemede kalır; burada basitlik için
        # limit fiyatından dolduğunu varsayıyoruz.
        fill_price = price if price is not None else (
            self._positions.get(symbol).entry_price if symbol in self._positions else 0.0)
        if fill_price <= 0:
            order.status = OrderStatus.REJECTED
            log.warning("Emir reddedildi (geçersiz fiyat): %s", oid)
            self._orders[oid] = order
            return order

        order.status = OrderStatus.FILLED
        order.filled_price = fill_price
        self._orders[oid] = order
        self._apply_fill(order)
        log.info("Emir DOLDU | %s %s %d @ %.4f | SL=%s TP=%s",
                 oid, side.value, quantity, fill_price, stop_loss, take_profit)
        return order

    def cancel_order(self, order_id: str) -> bool:
        order = self._orders.get(order_id)
        if order and order.status == OrderStatus.NEW:
            order.status = OrderStatus.CANCELLED
            log.info("Emir iptal edildi: %s", order_id)
            return True
        log.warning("İptal başarısız (bulunamadı/uygun değil): %s", order_id)
        return False

    def get_open_orders(self) -> List[Order]:
        return [o for o in self._orders.values() if o.status == OrderStatus.NEW]

    def get_positions(self) -> List[Position]:
        return list(self._positions.values())

    # ----- Simülasyon iç mantığı ------------------------------------------
    def _apply_fill(self, order: Order) -> None:
        """Dolan emri pozisyona uygular (aç/kapat/ters)."""
        self._charge_commission(order.filled_price * order.quantity)
        existing = self._positions.get(order.symbol)

        if existing is None:
            # Yeni pozisyon aç.
            self._positions[order.symbol] = Position(
                symbol=order.symbol, side=order.side, quantity=order.quantity,
                entry_price=order.filled_price, stop_loss=order.stop_loss,
                take_profit=order.take_profit,
            )
            return

        # Karşı yönde emir → mevcut pozisyonu kapat.
        if existing.side != order.side:
            self._close_position(order.symbol, order.filled_price, "karşı emir")
        else:
            # Aynı yön → basitlik için ortalama maliyetle ekleme yapmıyoruz;
            # mevcut pozisyonu koru (gerçek sistemde piramitleme eklenebilir).
            log.debug("Aynı yönde emir; pozisyon değişmedi: %s", order.symbol)

    def _charge_commission(self, notional: float) -> None:
        fee = notional * self._commission
        self.commission_paid += fee
        self.realized_pnl -= fee

    def _close_position(self, symbol: str, exit_price: float, why: str) -> None:
        pos = self._positions.pop(symbol, None)
        if not pos:
            return
        pnl = pos.unrealized_pnl(exit_price)
        # Kapanışta da komisyon.
        self._charge_commission(exit_price * pos.quantity)
        self.realized_pnl += pnl
        self.closed_trades.append({
            "symbol": symbol, "side": pos.side.value, "qty": pos.quantity,
            "entry": pos.entry_price, "exit": exit_price, "pnl": pnl,
            "reason": why,
        })
        log.info("Pozisyon KAPANDI | %s %s @ %.4f (giriş %.4f) | K/Z=%.2f | %s",
                 symbol, pos.side.value, exit_price, pos.entry_price, pnl, why)
        if self._on_close:
            self._on_close(pnl, self._now or datetime.utcnow())

    def mark_price(self, symbol: str, price: float,
                   ts: Optional[datetime] = None) -> None:
        """Cari fiyatı işler; stop-loss/take-profit tetiklenirse pozisyonu kapatır.

        Canlı/paper döngüde ve backtest'te her yeni mumda çağrılmalıdır.
        """
        if ts is not None:
            self._now = ts
        pos = self._positions.get(symbol)
        if not pos:
            return

        if pos.side == OrderSide.BUY:
            if pos.stop_loss is not None and price <= pos.stop_loss:
                self._close_position(symbol, pos.stop_loss, "stop-loss")
            elif pos.take_profit is not None and price >= pos.take_profit:
                self._close_position(symbol, pos.take_profit, "take-profit")
        else:  # SELL/short
            if pos.stop_loss is not None and price >= pos.stop_loss:
                self._close_position(symbol, pos.stop_loss, "stop-loss")
            elif pos.take_profit is not None and price <= pos.take_profit:
                self._close_position(symbol, pos.take_profit, "take-profit")

    def close_all(self, prices: Dict[str, float], why: str = "kapanış") -> None:
        """Tüm açık pozisyonları verilen fiyatlardan kapatır (seans/backtest sonu)."""
        for symbol in list(self._positions.keys()):
            price = prices.get(symbol, self._positions[symbol].entry_price)
            self._close_position(symbol, price, why)
