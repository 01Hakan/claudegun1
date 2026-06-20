"""
Risk Management Katmanı
=======================

Pozisyon boyutlandırma ve risk limitlerinin uygulanması.

Kurallar:
  1. İşlem başına maksimum risk: sermayenin ``risk_per_trade_pct`` yüzdesi.
  2. Günlük maksimum zarar: ``daily_max_loss_pct`` aşılırsa yeni pozisyon yok.
  3. Eşzamanlı açık pozisyon limiti: ``max_open_positions``.

Pozisyon boyutu formülü:
    risk_tutarı = bakiye * (risk_yüzdesi / 100)
    hisse_adedi = risk_tutarı / stop_mesafesi   (lot, aşağı yuvarlanır)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from bistrobot.logging_utils.logger import get_logger

log = get_logger("risk")


@dataclass
class RiskParams:
    """Risk yönetimi parametreleri (config'ten doldurulur)."""
    account_balance: float = 100_000.0
    risk_per_trade_pct: float = 1.0
    daily_max_loss_pct: float = 3.0
    max_open_positions: int = 3

    @classmethod
    def from_config(cls, risk_cfg: dict) -> "RiskParams":
        return cls(
            account_balance=float(risk_cfg.get("account_balance", 100_000.0)),
            risk_per_trade_pct=float(risk_cfg.get("risk_per_trade_pct", 1.0)),
            daily_max_loss_pct=float(risk_cfg.get("daily_max_loss_pct", 3.0)),
            max_open_positions=int(risk_cfg.get("max_open_positions", 3)),
        )


@dataclass
class RiskDecision:
    """Risk kontrol sonucu."""
    approved: bool
    quantity: int          # Onaylanan hisse adedi (red ise 0)
    reason: str


def position_size(balance: float, stop_distance: float,
                  risk_pct: float, price: Optional[float] = None) -> int:
    """Sabit-kesirli (fixed-fractional) pozisyon boyutu hesaplar.

    Args:
        balance: Hesap bakiyesi.
        stop_distance: Giriş ile stop-loss arasındaki mutlak fiyat farkı (>0).
        risk_pct: İşlem başına riske edilecek sermaye yüzdesi.
        price: (Opsiyonel) hisse fiyatı; verilirse pozisyon nominal değeri
            bakiyeyi aşamaz (kaldıraçsız varsayım, BIST spot için uygun).

    Returns:
        Alınacak hisse adedi (tam sayı, aşağı yuvarlanmış). Geçersiz girdide 0.
    """
    if balance <= 0 or stop_distance <= 0 or risk_pct <= 0:
        return 0
    risk_amount = balance * (risk_pct / 100.0)
    qty = math.floor(risk_amount / stop_distance)
    # Spot piyasada (kaldıraçsız) pozisyon değeri bakiyeyi aşamaz.
    if price and price > 0:
        max_affordable = math.floor(balance / price)
        qty = min(qty, max_affordable)
    return max(qty, 0)


class RiskManager:
    """Risk kurallarını uygulayan durum-bilgili (stateful) bileşen."""

    def __init__(self, params: RiskParams) -> None:
        self.p = params
        self._equity = params.account_balance      # Güncel öz sermaye
        self._day: Optional[date] = None           # İzlenen gün
        self._day_start_equity = params.account_balance
        self._realized_today = 0.0                  # Bugünkü gerçekleşmiş K/Z
        self._open_positions = 0
        self._halted = False                        # Güvenli duruş bayrağı

    # ----- Gün takibi ------------------------------------------------------
    def _roll_day(self, today: date) -> None:
        """Yeni güne geçildiyse günlük sayaçları sıfırlar."""
        if self._day != today:
            self._day = today
            self._day_start_equity = self._equity
            self._realized_today = 0.0
            log.info("Yeni işlem günü: %s | gün başı öz sermaye=%.2f",
                     today, self._equity)

    # ----- Durum güncellemeleri -------------------------------------------
    def register_open(self) -> None:
        self._open_positions += 1

    def register_close(self, pnl: float, today=None) -> None:
        """Bir pozisyon kapandığında K/Z'yi işler.

        ``today`` date veya datetime olabilir (datetime ise .date() alınır).
        """
        if isinstance(today, datetime):
            today = today.date()
        # Yeni güne geçildiyse, K/Z'yi eklemeden ÖNCE günü çevir ki
        # bu işlemin K/Z'si doğru güne yazılsın.
        if today:
            self._roll_day(today)
        self._open_positions = max(0, self._open_positions - 1)
        self._equity += pnl
        self._realized_today += pnl
        log.info("Pozisyon kapandı | K/Z=%.2f | gün toplamı=%.2f | öz sermaye=%.2f",
                 pnl, self._realized_today, self._equity)

    def sync_open_positions(self, count: int) -> None:
        """Açık pozisyon sayısını executor ile senkronize eder."""
        self._open_positions = count

    @property
    def equity(self) -> float:
        return self._equity

    @property
    def halted(self) -> bool:
        return self._halted

    def halt(self, reason: str) -> None:
        """Kritik hata vb. durumda güvenli duruş — yeni emirleri durdurur."""
        self._halted = True
        log.error("GÜVENLİ DURUŞ etkinleştirildi: %s", reason)

    def resume(self) -> None:
        self._halted = False
        log.warning("Güvenli duruş kaldırıldı; işlemler devam edebilir.")

    # ----- Günlük zarar limiti --------------------------------------------
    def daily_loss_breached(self, today: date) -> bool:
        """Günlük maksimum zarar limiti aşıldı mı?"""
        self._roll_day(today)
        limit = self._day_start_equity * (self.p.daily_max_loss_pct / 100.0)
        # _realized_today negatifse zarar; limit pozitif tutar.
        return (-self._realized_today) >= limit

    # ----- Ana karar fonksiyonu -------------------------------------------
    def evaluate(self, entry_price: float, stop_loss: float,
                 today: date) -> RiskDecision:
        """Bir giriş emrini risk kurallarına göre değerlendirir.

        Returns:
            RiskDecision(approved, quantity, reason)
        """
        self._roll_day(today)

        if self._halted:
            return RiskDecision(False, 0, "Güvenli duruş aktif")

        if self._open_positions >= self.p.max_open_positions:
            return RiskDecision(False, 0,
                                f"Maks. açık pozisyon limiti ({self.p.max_open_positions})")

        if self.daily_loss_breached(today):
            return RiskDecision(False, 0,
                                f"Günlük zarar limiti aşıldı "
                                f"(%{self.p.daily_max_loss_pct})")

        stop_distance = abs(entry_price - stop_loss)
        if stop_distance <= 0:
            return RiskDecision(False, 0, "Geçersiz stop mesafesi")

        qty = position_size(self._equity, stop_distance,
                            self.p.risk_per_trade_pct, entry_price)
        if qty <= 0:
            return RiskDecision(False, 0, "Hesaplanan pozisyon boyutu 0")

        return RiskDecision(True, qty,
                            f"Onaylandı: {qty} adet (risk=%{self.p.risk_per_trade_pct}, "
                            f"stop mesafe={stop_distance:.4f})")
