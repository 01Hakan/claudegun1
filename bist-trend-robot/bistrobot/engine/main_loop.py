"""
Engine Katmanı — MainLoop / Scheduler
=====================================

Canlı ve paper trading modlarını yöneten ana çalışma döngüsü.

Çalışma mantığı (her ``poll_interval_sec`` saniyede bir):
  1. Her sembol için en son TAMAMLANMIŞ mumu çek.
  2. Yeni bir 1 saatlik mum oluştuysa:
     a. Stratejiyi çalıştır → sinyal üret.
     b. Risk kurallarını kontrol et.
     c. Uygunsa emir oluştur/gönder.
  3. Açık pozisyonların stop-loss / take-profit kontrolünü yap.

Hata yönetimi:
  - Veri/emir hatalarında üstel geri-çekilmeli (exponential backoff) retry.
  - Ardışık kritik hatalarda RiskManager.halt() ile güvenli duruş.
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Callable, Dict, List, Optional, TypeVar

from bistrobot.data.provider import Candle, IDataProvider
from bistrobot.execution.executor import IOrderExecutor, OrderSide, PriceType
from bistrobot.logging_utils.logger import get_logger
from bistrobot.risk.manager import RiskManager
from bistrobot.strategy.base import SignalType, Strategy

log = get_logger("engine.mainloop")

T = TypeVar("T")


def retry(fn: Callable[[], T], attempts: int = 4, base_delay: float = 2.0,
          sleeper: Callable[[float], None] = time.sleep) -> T:
    """Üstel geri-çekilmeli yeniden deneme (2s, 4s, 8s, 16s ...).

    Args:
        fn: Çağrılacak fonksiyon.
        attempts: Maks. deneme sayısı.
        base_delay: İlk bekleme süresi; her denemede ikiye katlanır.
        sleeper: Bekleme fonksiyonu (test edilebilirlik için enjekte edilir).
    """
    last_exc: Optional[Exception] = None
    for n in range(attempts):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 — geniş yakalama bilinçli
            last_exc = exc
            delay = base_delay * (2 ** n)
            log.warning("İşlem hatası (deneme %d/%d): %s — %.0fs sonra tekrar",
                        n + 1, attempts, exc, delay)
            if n < attempts - 1:
                sleeper(delay)
    assert last_exc is not None
    raise last_exc


class MainLoop:
    """Robotun canlı/paper çalışma döngüsünü yöneten orkestratör."""

    def __init__(self, symbols: List[str], timeframe: str,
                 data: IDataProvider, strategy: Strategy,
                 risk: RiskManager, executor: IOrderExecutor,
                 poll_interval_sec: int = 60, is_live: bool = False) -> None:
        self.symbols = symbols
        self.timeframe = timeframe
        self.data = data
        self.strategy = strategy
        self.risk = risk
        self.executor = executor
        self.poll_interval = poll_interval_sec
        self.is_live = is_live
        # Sembol başına son işlenen mum zaman damgası (yeni mum tespiti için).
        self._last_ts: Dict[str, Optional[datetime]] = {s: None for s in symbols}
        self._consecutive_errors = 0

    def run(self, iterations: Optional[int] = None,
            sleeper: Callable[[float], None] = time.sleep) -> None:
        """Döngüyü çalıştırır.

        Args:
            iterations: None ise sonsuz; aksi halde belirtilen tur sayısı
                (paper/test için).
            sleeper: Bekleme fonksiyonu (test'te no-op verilebilir).
        """
        mode = "CANLI (GERÇEK PARA)" if self.is_live else "PAPER (SİMÜLASYON, gerçek para YOK)"
        log.info("MainLoop başladı | mod=%s | %d sembol | tf=%s",
                 mode, len(self.symbols), self.timeframe)

        count = 0
        while iterations is None or count < iterations:
            try:
                self._tick()
                self._consecutive_errors = 0
            except Exception as exc:  # noqa: BLE001
                self._consecutive_errors += 1
                log.error("Döngü hatası: %s (ardışık=%d)", exc, self._consecutive_errors)
                if self._consecutive_errors >= 3:
                    self.risk.halt("Ardışık 3 kritik hata — güvenli duruş")
            count += 1
            if iterations is None or count < iterations:
                sleeper(self.poll_interval)

        log.info("MainLoop sonlandı (%d tur).", count)

    def _tick(self) -> None:
        """Tek bir döngü adımı: veri çek, sinyal üret, riski uygula, emir gönder."""
        for symbol in self.symbols:
            # En son tamamlanmış mumu retry ile çek.
            candle: Candle = retry(
                lambda s=symbol: self.data.get_latest_candle(s, self.timeframe))

            # Yeni mum mu? (Aynı zaman damgası ise işleme alma.)
            if self._last_ts[symbol] is not None and candle.timestamp <= self._last_ts[symbol]:
                continue
            self._last_ts[symbol] = candle.timestamp

            # Strateji için yeterli geçmiş + güncel mum penceresi.
            history = retry(lambda s=symbol: self.data.get_historical_candles(
                s, self.timeframe, self.strategy.min_candles + 5))
            window = self._merge(history, candle)

            self._process_symbol(symbol, window)

    def _process_symbol(self, symbol: str, window: List[Candle]) -> None:
        price = window[-1].close
        ts = window[-1].timestamp

        # 1) Açık pozisyon stop/TP kontrolü (mock executor için).
        mark = getattr(self.executor, "mark_price", None)
        if callable(mark):
            mark(symbol, price, ts)

        # 2) Sinyal üret.
        signal = self.strategy.generate_signal(window)
        self.risk.sync_open_positions(len(self.executor.get_positions()))
        open_symbols = {p.symbol for p in self.executor.get_positions()}

        if signal.type == SignalType.HOLD:
            return

        if signal.type == SignalType.BUY and symbol not in open_symbols:
            if signal.stop_loss is None:
                return
            decision = self.risk.evaluate(price, signal.stop_loss, ts.date())
            if not decision.approved:
                log.info("[%s] BUY reddedildi: %s", symbol, decision.reason)
                return
            # >>> GERÇEK API ENTEGRASYON NOKTASI:
            #     is_live=True iken bu çağrı gerçek aracı kuruma gider.
            retry(lambda: self.executor.create_order(
                symbol, OrderSide.BUY, decision.quantity, PriceType.MARKET,
                price=price, stop_loss=signal.stop_loss,
                take_profit=signal.take_profit))
            self.risk.register_open()

        elif signal.type == SignalType.SELL and symbol in open_symbols:
            qty = next((p.quantity for p in self.executor.get_positions()
                        if p.symbol == symbol), 0)
            if qty > 0:
                retry(lambda: self.executor.create_order(
                    symbol, OrderSide.SELL, qty, PriceType.MARKET, price=price))

    @staticmethod
    def _merge(history: List[Candle], latest: Candle) -> List[Candle]:
        """Geçmiş mumlara en güncel mumu ekler (zaman damgası tekrarını önler)."""
        if history and history[-1].timestamp == latest.timestamp:
            return history
        return history + [latest]
