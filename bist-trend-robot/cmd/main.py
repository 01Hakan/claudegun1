"""
BIST Kısa Vadeli Trend Trade Robotu — Giriş Noktası (main)
==========================================================

Çalıştırma örnekleri:
    python -m cmd.main --mode backtest --config config/config.yaml
    python -m cmd.main --mode paper    --config config/config.yaml --iterations 5
    python -m cmd.main --mode live     --config config/config.yaml

⚠️ UYARI: Bu yazılım EĞİTİM/DENEYSEL amaçlıdır. Gerçek kâr garantisi YOKTUR.
Gerçek para ile kullanmadan önce uzun süreli backtest ve paper trading yapın.
Tüm finansal sorumluluk ve risk kullanıcıya aittir. Yerel sermaye piyasası
mevzuatına ve aracı kurum koşullarına uymak sizin yükümlülüğünüzdür.
"""

from __future__ import annotations

import argparse
import sys

from bistrobot.backtest.engine import Backtester
from bistrobot.config.loader import ConfigError, load_config
from bistrobot.data.mock_provider import MockDataProvider
from bistrobot.data.provider import IDataProvider
from bistrobot.engine.main_loop import MainLoop
from bistrobot.execution.executor import IOrderExecutor
from bistrobot.execution.mock_executor import MockOrderExecutor
from bistrobot.logging_utils.logger import configure_logging, get_logger
from bistrobot.risk.manager import RiskManager, RiskParams
from bistrobot.strategy.trend_strategy import TrendParams, TrendStrategy

log = get_logger("main")


# ---------------------------------------------------------------------------
# Fabrika fonksiyonları — gerçek API'ye geçişte yalnızca burayı değiştirin.
# ---------------------------------------------------------------------------
def build_data_provider(cfg: dict) -> IDataProvider:
    """Veri sağlayıcıyı üretir.

    # >>> GERÇEK API ENTEGRASYON NOKTASI:
    #     cfg["broker"]["name"] == "MockBroker" değilse, gerçek aracı kurumun
    #     IDataProvider implementasyonunu döndürün.
    """
    bars = int(cfg.get("backtest", {}).get("bars", 1500))
    return MockDataProvider(seed=42, bars=bars)


def build_executor(cfg: dict, risk: RiskManager) -> IOrderExecutor:
    """Emir yürütücüyü üretir.

    # >>> GERÇEK API ENTEGRASYON NOKTASI:
    #     Canlı modda BrokerOrderExecutor(api_key=..., api_secret=...) döndürün.
    """
    commission = float(cfg.get("backtest", {}).get("commission_pct", 0.0))
    # register_close datetime/date'in ikisini de kabul eder.
    return MockOrderExecutor(commission_pct=commission, on_close=risk.register_close)


def build_strategy(cfg: dict) -> TrendStrategy:
    return TrendStrategy(TrendParams.from_config(cfg["strategy"]))


# ---------------------------------------------------------------------------
# Mod çalıştırıcıları
# ---------------------------------------------------------------------------
def run_backtest(cfg: dict) -> int:
    log.info("=== BACKTEST MODU ===")
    strategy = build_strategy(cfg)
    risk_params = RiskParams.from_config(cfg["risk"])
    risk_params.account_balance = float(
        cfg.get("backtest", {}).get("initial_balance", risk_params.account_balance))
    commission = float(cfg.get("backtest", {}).get("commission_pct", 0.0))

    provider = MockDataProvider(seed=42, bars=int(cfg.get("backtest", {}).get("bars", 1500)))
    data = {sym: provider.full_series(sym, cfg["app"]["timeframe"])
            for sym in cfg["symbols"]}

    bt = Backtester(strategy, risk_params, commission)
    result = bt.run(data)
    print(result.summary())
    return 0


def run_live_or_paper(cfg: dict, is_live: bool, iterations) -> int:
    mode_name = "CANLI" if is_live else "PAPER (gerçek para YOK)"
    log.info("=== %s MODU ===", mode_name)
    if is_live and "PLACEHOLDER" in str(cfg["broker"]["api_key"]):
        log.error("Canlı mod için gerçek API anahtarı gerekli (config PLACEHOLDER).")
        return 2

    strategy = build_strategy(cfg)
    risk = RiskManager(RiskParams.from_config(cfg["risk"]))
    data = build_data_provider(cfg)
    executor = build_executor(cfg, risk)

    loop = MainLoop(
        symbols=cfg["symbols"], timeframe=cfg["app"]["timeframe"],
        data=data, strategy=strategy, risk=risk, executor=executor,
        poll_interval_sec=int(cfg["app"].get("poll_interval_sec", 60)),
        is_live=is_live,
    )
    # Paper/test'te beklemeyi kısaltmak için no-op sleeper kullanılabilir.
    sleeper = (lambda _s: None) if not is_live else __import__("time").sleep
    loop.run(iterations=iterations, sleeper=sleeper)

    # Paper modda özet.
    if isinstance(executor, MockOrderExecutor):
        log.info("Paper özet | gerçekleşen K/Z=%.2f | açık pozisyon=%d | komisyon=%.2f",
                 executor.realized_pnl, len(executor.get_positions()),
                 executor.commission_paid)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="BIST Trend Trade Robotu")
    parser.add_argument("--config", default="config/config.yaml",
                        help="Config dosyası yolu")
    parser.add_argument("--mode", choices=["backtest", "paper", "live"],
                        help="Çalışma modu (config'i ezer)")
    parser.add_argument("--iterations", type=int, default=10,
                        help="Paper/live döngü tur sayısı (test için)")
    args = parser.parse_args(argv)

    try:
        cfg = load_config(args.config)
    except ConfigError as exc:
        print(f"Config hatası: {exc}", file=sys.stderr)
        return 1

    mode = args.mode or cfg["app"]["mode"]
    configure_logging(
        level=cfg.get("logging", {}).get("level", "INFO"),
        to_file=bool(cfg.get("logging", {}).get("to_file", False)),
        file_path=cfg.get("logging", {}).get("file_path", "logs/robot.log"),
    )

    if mode == "backtest":
        return run_backtest(cfg)
    if mode == "paper":
        return run_live_or_paper(cfg, is_live=False, iterations=args.iterations)
    if mode == "live":
        return run_live_or_paper(cfg, is_live=True, iterations=args.iterations)
    print(f"Bilinmeyen mod: {mode}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
