"""
Backtest Modülü
===============

Geçmiş (veya sentetik) mum verisi üzerinde stratejiyi mum-mum çalıştırır,
risk yönetimi ve mock executor'ı kullanarak işlemleri simüle eder ve
performans metriklerini raporlar.

Metrikler:
  - Toplam getiri (%) ve net K/Z
  - Maksimum düşüş (max drawdown, %)
  - İşlem sayısı, kazanma oranı (%)
  - Basit Sharpe benzeri oran (ortalama getiri / getiri std, yıllıklandırılmış)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List

from bistrobot.data.provider import Candle
from bistrobot.execution.executor import OrderSide, PriceType
from bistrobot.execution.mock_executor import MockOrderExecutor
from bistrobot.logging_utils.logger import get_logger
from bistrobot.risk.manager import RiskManager, RiskParams
from bistrobot.strategy.base import SignalType, Strategy

log = get_logger("backtest")


@dataclass
class BacktestResult:
    """Backtest çıktısı / performans raporu."""
    initial_balance: float
    final_equity: float
    total_return_pct: float
    max_drawdown_pct: float
    num_trades: int
    win_rate_pct: float
    sharpe: float
    commission_paid: float
    trades: List[dict] = field(default_factory=list)

    def summary(self) -> str:
        return (
            "===== BACKTEST SONUCU =====\n"
            f"Başlangıç bakiye : {self.initial_balance:,.2f}\n"
            f"Son öz sermaye   : {self.final_equity:,.2f}\n"
            f"Toplam getiri    : %{self.total_return_pct:.2f}\n"
            f"Maks. düşüş (DD) : %{self.max_drawdown_pct:.2f}\n"
            f"İşlem sayısı     : {self.num_trades}\n"
            f"Kazanma oranı    : %{self.win_rate_pct:.2f}\n"
            f"Sharpe (basit)   : {self.sharpe:.2f}\n"
            f"Ödenen komisyon  : {self.commission_paid:,.2f}\n"
            "==========================="
        )


class Backtester:
    """Tek sembol veya çok sembollü backtest yürütücüsü."""

    def __init__(self, strategy: Strategy, risk_params: RiskParams,
                 commission_pct: float = 0.0) -> None:
        self.strategy = strategy
        self.risk_params = risk_params
        self.commission_pct = commission_pct

    def run(self, candles_by_symbol: Dict[str, List[Candle]]) -> BacktestResult:
        """Verilen sembol->mum verisi sözlüğü üzerinde backtest yapar.

        Tüm semboller aynı zaman ekseninde, bar-bar ilerletilir.
        """
        risk = RiskManager(self.risk_params)
        executor = MockOrderExecutor(self.commission_pct, on_close=risk.register_close)

        symbols = list(candles_by_symbol.keys())
        max_len = max(len(c) for c in candles_by_symbol.values())
        warmup = self.strategy.min_candles

        equity_curve: List[float] = [self.risk_params.account_balance]

        # Bar-bar ilerle (warm-up'tan sonra sinyal üretmeye başla).
        for i in range(warmup, max_len):
            for symbol in symbols:
                series = candles_by_symbol[symbol]
                if i >= len(series):
                    continue
                window = series[:i + 1]
                price = window[-1].close
                ts = window[-1].timestamp

                # 1) Açık pozisyonlar için stop/TP kontrolü (cari fiyatla).
                executor.mark_price(symbol, price, ts)

                # 2) Sinyal üret.
                signal = self.strategy.generate_signal(window)
                risk.sync_open_positions(len(executor.get_positions()))

                open_symbols = {p.symbol for p in executor.get_positions()}

                if signal.type == SignalType.BUY and symbol not in open_symbols:
                    if signal.stop_loss is None:
                        continue
                    decision = risk.evaluate(price, signal.stop_loss, ts.date())
                    if decision.approved:
                        executor.create_order(
                            symbol, OrderSide.BUY, decision.quantity,
                            PriceType.MARKET, price=price,
                            stop_loss=signal.stop_loss,
                            take_profit=signal.take_profit)
                        risk.register_open()
                    else:
                        log.debug("[%s] BUY reddedildi: %s", symbol, decision.reason)

                elif signal.type == SignalType.SELL and symbol in open_symbols:
                    # Mevcut long'u kapat (karşı emir).
                    executor.create_order(symbol, OrderSide.SELL,
                                          self._qty(executor, symbol),
                                          PriceType.MARKET, price=price)

            # Bar sonu öz sermaye (gerçekleşen + açık pozisyon değerlemesi).
            equity_curve.append(self._mark_to_market(executor, candles_by_symbol, i))

        # Backtest sonu: tüm pozisyonları son fiyatlardan kapat.
        last_prices = {s: candles_by_symbol[s][min(max_len, len(candles_by_symbol[s])) - 1].close
                       for s in symbols}
        executor.close_all(last_prices, "backtest sonu")
        final_equity = self.risk_params.account_balance + executor.realized_pnl

        return self._build_result(executor, equity_curve, final_equity)

    # ----- yardımcılar -----------------------------------------------------
    @staticmethod
    def _qty(executor: MockOrderExecutor, symbol: str) -> int:
        for p in executor.get_positions():
            if p.symbol == symbol:
                return p.quantity
        return 0

    def _mark_to_market(self, executor: MockOrderExecutor,
                        data: Dict[str, List[Candle]], i: int) -> float:
        """Gerçekleşen K/Z + açık pozisyonların cari değerlemesi."""
        equity = self.risk_params.account_balance + executor.realized_pnl
        for pos in executor.get_positions():
            series = data[pos.symbol]
            price = series[min(i, len(series) - 1)].close
            equity += pos.unrealized_pnl(price)
        return equity

    def _build_result(self, executor: MockOrderExecutor,
                      equity_curve: List[float], final_equity: float) -> BacktestResult:
        initial = self.risk_params.account_balance
        total_return = (final_equity - initial) / initial * 100.0 if initial else 0.0

        # Maksimum düşüş.
        peak = equity_curve[0]
        max_dd = 0.0
        for eq in equity_curve:
            peak = max(peak, eq)
            if peak > 0:
                dd = (peak - eq) / peak * 100.0
                max_dd = max(max_dd, dd)

        trades = executor.closed_trades
        wins = [t for t in trades if t["pnl"] > 0]
        win_rate = (len(wins) / len(trades) * 100.0) if trades else 0.0

        sharpe = self._sharpe(equity_curve)

        result = BacktestResult(
            initial_balance=initial, final_equity=final_equity,
            total_return_pct=total_return, max_drawdown_pct=max_dd,
            num_trades=len(trades), win_rate_pct=win_rate, sharpe=sharpe,
            commission_paid=executor.commission_paid, trades=trades,
        )
        log.info("Backtest tamamlandı: %d işlem, getiri %%%.2f, DD %%%.2f",
                 result.num_trades, result.total_return_pct, result.max_drawdown_pct)
        return result

    @staticmethod
    def _sharpe(equity_curve: List[float],
                periods_per_year: int = 252 * 7) -> float:
        """Bar-getirilerinden basit yıllıklandırılmış Sharpe (risksiz oran=0).

        periods_per_year: 1 saatlik BIST barı ≈ günde 7 bar (10:00–18:00) * 252 gün.
        """
        rets: List[float] = []
        for a, b in zip(equity_curve, equity_curve[1:]):
            if a > 0:
                rets.append((b - a) / a)
        if len(rets) < 2:
            return 0.0
        mean = sum(rets) / len(rets)
        var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
        std = math.sqrt(var)
        if std == 0:
            return 0.0
        return (mean / std) * math.sqrt(periods_per_year)
