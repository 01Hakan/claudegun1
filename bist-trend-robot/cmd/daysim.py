"""
Tek Gün "Ne Olurdu?" Simülatörü (Day What-If)
=============================================

Belirli BIR işlem gününde, 100.000 TL başlangıç sermayesiyle robotun
GERÇEK (veya sentetik) intraday veriyle ne yapacağını simüle eder ve gün
sonu sonucunu raporlar.

Mantık:
  - Hedef günden ÖNCEKİ barlar yalnızca indikatör ısınması (warm-up) için
    kullanılır; o barlarda işlem AÇILMAZ.
  - Hedef gün içindeki barlarda strateji normal çalışır: sinyal → risk →
    emir. Stop-loss / take-profit gün içinde tetiklenebilir.
  - Gün sonunda açık kalan pozisyonlar son fiyattan değerlenir (mark-to-market)
    ve K/Z'ye yansıtılır → "bugün ne kazandırırdı/kaybettirirdi" net görülür.

Kullanım:
    # Gerçek veri (internet erişimi olan ortamda):
    python -m cmd.daysim --provider yahoo --balance 100000
    python -m cmd.daysim --provider yahoo --date 2024-06-14

    # Sentetik veri ile (offline demo — GERÇEK DEĞİL):
    python -m cmd.daysim --provider mock

⚠️ UYARI: Bu bir GEÇMİŞE DÖNÜK ("ne olurdu") simülasyondur; gelecek
performans garantisi DEĞİLDİR. Tek günlük sonuç istatistiksel olarak
anlamsızdır — strateji başarısı ancak uzun dönemli backtest ve paper
trading ile değerlendirilebilir. Tüm risk kullanıcıya aittir.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime
from typing import Dict, List, Optional

from bistrobot.backtest.engine import Backtester
from bistrobot.config.loader import ConfigError, load_config
from bistrobot.data.mock_provider import MockDataProvider
from bistrobot.data.provider import Candle, IDataProvider
from bistrobot.data.yahoo_provider import YahooDataProvider
from bistrobot.logging_utils.logger import configure_logging, get_logger
from bistrobot.risk.manager import RiskParams
from bistrobot.strategy.trend_strategy import TrendParams, TrendStrategy

log = get_logger("daysim")


def _make_provider(name: str, cfg: dict) -> IDataProvider:
    if name == "yahoo":
        return YahooDataProvider()
    # Sentetik: demo için yeterli geçmiş üret.
    return MockDataProvider(seed=42, bars=int(cfg.get("backtest", {}).get("bars", 1500)))


def _fetch(provider: IDataProvider, symbol: str, timeframe: str,
           limit: int) -> List[Candle]:
    """Tek sembol için geçmiş seriyi çeker; hata olursa boş liste döner."""
    try:
        full = getattr(provider, "full_series", None)
        if callable(full):
            return full(symbol, timeframe)
        return provider.get_historical_candles(symbol, timeframe, limit)
    except Exception as exc:  # noqa: BLE001
        log.error("[%s] veri alınamadı: %s", symbol, exc)
        return []


def _pick_target_day(data: Dict[str, List[Candle]],
                     wanted: Optional[str]) -> date:
    """Hedef günü belirler: --date verildiyse onu, yoksa en son işlem gününü."""
    if wanted:
        return datetime.strptime(wanted, "%Y-%m-%d").date()
    last = max(c[-1].timestamp.date() for c in data.values() if c)
    return last


def run_day_sim(cfg: dict, provider_name: str, balance: float,
                wanted_date: Optional[str], timeframe: str) -> int:
    strategy = TrendStrategy(TrendParams.from_config(cfg["strategy"]))
    risk_params = RiskParams.from_config(cfg["risk"])
    risk_params.account_balance = balance
    commission = float(cfg.get("backtest", {}).get("commission_pct", 0.0))
    symbols = cfg["symbols"]

    provider = _make_provider(provider_name, cfg)
    is_real = provider_name == "yahoo"

    # Warm-up + en az birkaç gün veri çek.
    limit = max(strategy.min_candles * 4, 500)
    data = {s: _fetch(provider, s, timeframe, limit) for s in symbols}
    data = {s: c for s, c in data.items() if c}
    if not data:
        log.error("Veri alınamadı. (Gerçek veri için internet erişimi gerekir; "
                  "kısıtlı ağda 'yahoo' başarısız olur.)")
        return 1

    target = _pick_target_day(data, wanted_date)
    trade_from = datetime(target.year, target.month, target.day, 0, 0, 0)

    # Hedef güne ait bar var mı ve yeterli ısınma var mı kontrol et.
    day_bars: Dict[str, int] = {}
    warmup_ok: Dict[str, int] = {}
    for s, candles in data.items():
        day_bars[s] = sum(1 for c in candles if c.timestamp.date() == target)
        warmup_ok[s] = sum(1 for c in candles if c.timestamp.date() < target)

    tradable = {s: n for s, n in day_bars.items() if n > 0}
    if not tradable:
        log.error("Hedef gün (%s) için veri bulunamadı. Mevcut son gün: %s",
                  target, max(c[-1].timestamp.date() for c in data.values()))
        return 1

    bt = Backtester(strategy, risk_params, commission)
    result = bt.run(data, trade_from_ts=trade_from)

    _print_report(result, target, is_real, timeframe, balance,
                  day_bars, warmup_ok, strategy.min_candles)
    return 0


def _print_report(result, target: date, is_real: bool, timeframe: str,
                  balance: float, day_bars: dict, warmup_ok: dict,
                  min_candles: int) -> None:
    src = "GERÇEK (Yahoo Finance)" if is_real else "SENTETİK (DEMO — gerçek değil!)"
    pnl = result.final_equity - balance
    sign = "+" if pnl >= 0 else ""

    print("\n" + "=" * 60)
    print("        TEK GÜN 'NE OLURDU?' SİMÜLASYON RAPORU")
    print("=" * 60)
    print(f"Veri kaynağı     : {src}")
    print(f"Hedef gün        : {target}  (zaman dilimi: {timeframe})")
    print(f"Başlangıç sermaye: {balance:,.2f} TL")
    print(f"Gün sonu sermaye : {result.final_equity:,.2f} TL")
    print(f"Gün K/Z          : {sign}{pnl:,.2f} TL  ({sign}{result.total_return_pct:.2f}%)")
    print("-" * 60)
    print(f"İşlem sayısı     : {result.num_trades}")
    print(f"Kazanan oran     : %{result.win_rate_pct:.1f}")
    print(f"Gün içi max düşüş : %{result.max_drawdown_pct:.2f}")
    print(f"Ödenen komisyon  : {result.commission_paid:,.2f} TL")
    print("-" * 60)
    print("Sembol bazında o güne ait bar / ısınma barı sayısı:")
    for s in day_bars:
        warn = "" if warmup_ok.get(s, 0) >= min_candles else "  (⚠ ısınma yetersiz!)"
        print(f"  {s:<10} gün barı={day_bars[s]:<3} ısınma={warmup_ok.get(s,0):<4}{warn}")

    if result.trades:
        print("-" * 60)
        print("İşlem detayları:")
        print(f"  {'SEMBOL':<10}{'YÖN':<5}{'ADET':>6}  {'GİRİŞ':>9}  {'ÇIKIŞ':>9}  "
              f"{'K/Z':>10}  NEDEN")
        for t in result.trades:
            print(f"  {t['symbol']:<10}{t['side']:<5}{t['qty']:>6}  "
                  f"{t['entry']:>9.2f}  {t['exit']:>9.2f}  {t['pnl']:>+10.2f}  {t['reason']}")
    else:
        print("-" * 60)
        print("Bu gün hiç işlem açılmadı (strateji uygun sinyal üretmedi veya")
        print("risk kuralları engelledi).")

    print("=" * 60)
    print("⚠ UYARI: Bu GEÇMİŞE DÖNÜK bir simülasyondur, gelecek garantisi")
    print("  DEĞİLDİR. Tek günlük sonuç istatistiksel olarak anlamsızdır.")
    print("  Gerçek para öncesi uzun backtest + paper trading şarttır.")
    print("=" * 60 + "\n")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="BIST tek gün 'ne olurdu' simülatörü")
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--provider", choices=["yahoo", "mock"], default=None,
                        help="Veri kaynağı (varsayılan: config'teki data.provider)")
    parser.add_argument("--balance", type=float, default=100_000.0,
                        help="Başlangıç sermayesi (TL)")
    parser.add_argument("--date", default=None,
                        help="Hedef gün YYYY-MM-DD (yoksa en son işlem günü)")
    parser.add_argument("--timeframe", default=None,
                        help="Zaman dilimi (yoksa config'teki app.timeframe)")
    args = parser.parse_args(argv)

    try:
        cfg = load_config(args.config)
    except ConfigError as exc:
        print(f"Config hatası: {exc}", file=sys.stderr)
        return 1

    configure_logging(level=cfg.get("logging", {}).get("level", "INFO"))
    provider = args.provider or str(cfg.get("data", {}).get("provider", "mock")).lower()
    timeframe = args.timeframe or cfg["app"]["timeframe"]
    return run_day_sim(cfg, provider, args.balance, args.date, timeframe)


if __name__ == "__main__":
    raise SystemExit(main())
