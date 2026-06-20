# BIST Kısa Vadeli Trend Trade Robotu

> ⚠️ **ÖNEMLİ UYARI / DISCLAIMER**
> Bu proje **yalnızca eğitim ve deneysel amaçlıdır**. Hiçbir şekilde yatırım
> tavsiyesi değildir ve gerçek piyasalarda **kesin kâr garantisi vermez**.
> Gerçek para ile kullanmadan önce **uzun süreli backtest ve paper trading**
> yapın. Yerel sermaye piyasası mevzuatına, vergi düzenlemelerine ve aracı
> kurumunuzun kullanım koşullarına uymak sizin sorumluluğunuzdadır. Tüm
> finansal riski **tamamen siz üstlenirsiniz**.

Borsa İstanbul (BIST) hisseleri için kısa vadeli (varsayılan: 1 saatlik
periyot) trend analizi yaparak al/sat sinyalleri üreten, modüler ve
genişletilebilir bir algoritmik trade robotu iskeleti.

## Özellikler

- **Katmanlı mimari**: Data, Strategy, Execution, Risk, Logging, Config
  katmanları birbirinden bağımsız ve arayüzlerle (interface) gevşek bağlı.
- **Çoklu çalışma modu**:
  - `backtest`  → geçmiş veride strateji performansını ölçer.
  - `paper`     → gerçek zamanlı akışı simüle eder, **gerçek para kullanmaz**.
  - `live`      → gerçek aracı kurum API'sine emir gönderir (entegrasyon
    noktaları kod içinde yorumlarla işaretlenmiştir).
- **Soyut arayüzler**: `IDataProvider` ve `IOrderExecutor` sayesinde farklı
  veri sağlayıcılar / aracı kurumlar kolayca takılıp çıkarılabilir.
- **Gerçek veri**: Yahoo Finance entegrasyonu (`YahooDataProvider`) ile API
  anahtarı GEREKMEDEN gerçek BIST mum verisi (semboller otomatik `.IS`'e
  eşlenir). Offline geliştirme için sentetik `MockDataProvider` da mevcut.
- **İndikatörler**: SMA, EMA, RSI, MACD, ATR (saf Python, harici bağımlılık
  gerektirmez).
- **Risk yönetimi**: işlem başına risk %, günlük zarar limiti, eşzamanlı
  pozisyon limiti, ATR tabanlı stop-loss ve 1:2 risk/ödül take-profit.
- **Birim testleri**: indikatör, sinyal, risk ve pozisyon-boyutu hesapları.

## Mimari Özet

```
                 ┌──────────────┐
                 │  Config (YAML)│
                 └──────┬───────┘
                        │ parametreler
        ┌───────────────┼────────────────────────────┐
        ▼               ▼                             ▼
┌───────────────┐ ┌──────────────┐            ┌──────────────┐
│ Data Katmanı  │ │ Strategy     │  sinyal    │ Risk Yönetimi│
│ IDataProvider │►│ TrendStrategy│───────────►│ RiskManager  │
│ (mum verisi)  │ │ (EMA/RSI/MACD│            │ (boyut, limit│
└───────────────┘ │  /ATR)       │            │  stop/TP)    │
                  └──────────────┘            └──────┬───────┘
                                                     │ onaylı emir
                                                     ▼
                                            ┌──────────────────┐
                                            │ Execution Katmanı│
                                            │ IOrderExecutor   │
                                            │ MockOrderExecutor│
                                            └──────────────────┘
        Tümünü süren: MainLoop (Scheduler)  ·  Her adım: Logger
```

## Proje Yapısı

```
bist-trend-robot/
├── README.md
├── requirements.txt
├── config/
│   └── config.yaml              # API anahtarları (placeholder), semboller, parametreler
├── cmd/
│   └── main.py                  # Giriş noktası: backtest / paper / live modları
├── bistrobot/                   # Çekirdek paket (pkg / internal karşılığı)
│   ├── config/loader.py         # Config okuma + doğrulama
│   ├── data/provider.py         # IDataProvider arayüzü + Candle modeli
│   ├── data/mock_provider.py    # Sentetik/örnek veri sağlayıcı
│   ├── data/yahoo_provider.py   # GERÇEK BIST verisi (Yahoo Finance, read-only)
│   ├── strategy/indicators.py   # SMA, EMA, RSI, MACD, ATR
│   ├── strategy/base.py         # Strategy arayüzü + Signal modeli
│   ├── strategy/trend_strategy.py
│   ├── risk/manager.py          # Risk kuralları + pozisyon boyutu
│   ├── execution/executor.py    # IOrderExecutor arayüzü + Order/Position
│   ├── execution/mock_executor.py
│   ├── backtest/engine.py       # Backtest motoru + metrikler
│   ├── logging_utils/logger.py  # Yapılandırılmış loglama
│   └── engine/main_loop.py      # Scheduler / canlı & paper döngüsü
└── tests/
    ├── test_indicators.py
    ├── test_strategy.py
    ├── test_risk.py
    └── test_executor.py
```

## Kurulum

```bash
cd bist-trend-robot
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt        # PyYAML (opsiyonel) + pytest
```

> Not: PyYAML kurulu değilse config loader otomatik olarak gömülü basit bir
> YAML ayrıştırıcıya/JSON'a düşer; çekirdek robot harici bağımlılık olmadan
> da çalışır.

## Kullanım

```bash
# Backtest (geçmiş/sentetik veri üzerinde performans ölçümü)
python -m cmd.main --mode backtest --config config/config.yaml

# Paper trading (gerçek para YOK, simülasyon) — birkaç döngü çalıştırır
python -m cmd.main --mode paper --config config/config.yaml --iterations 5

# Canlı mod (gerçek API entegrasyonu gerektirir — varsayılan kapalı)
python -m cmd.main --mode live --config config/config.yaml
```

## Testler

```bash
cd bist-trend-robot
python -m pytest tests/ -v
# veya harici bağımlılık olmadan:
python -m unittest discover -s tests -v
```

## Gerçek BIST Verisi (Yahoo Finance)

`config/config.yaml` içindeki `data.provider` anahtarı ile veri kaynağı seçilir:

```yaml
data:
  provider: "yahoo"   # "yahoo" = gerçek BIST verisi · "mock" = sentetik/offline
```

`YahooDataProvider`:
- API anahtarı **gerektirmez**, saf Python (`urllib`) — ek bağımlılık yok.
- Sembol eşlemesi otomatik: `AKBNK.E` / `AKBNK` → `AKBNK.IS` (Yahoo formatı).
- `1m / 5m / 15m / 30m / 1h / 1d` intraday mum desteği.
- Yalnızca **tamamlanmış** mumları döndürür (oluşmakta olan yarım son mum
  filtrelenir) → look-ahead/yanıltıcı sinyal önlenir.
- Üstel geri-çekilmeli retry; zaman damgaları Europe/Istanbul'a çevrilir.

> ⚠️ **Ağ erişimi gerekir.** Yahoo verisi ücretsiz, gecikmeli ve resmî
> değildir; eğitim/geliştirme ve backtest içindir. Kısıtlı ağ ortamlarında
> (ör. allowlist'li çalıştırma ortamları) `query1.finance.yahoo.com`
> erişime açık değilse istek başarısız olur — bu durumda ya ağ politikasını
> bu hosta izin verecek şekilde ayarlayın ya da `provider: "mock"` kullanın.
> Canlı emir akışı için aracı kurumunuzun resmî API'sini tercih edin.

## Gerçek API'ye Geçiş

`live` modda gerçek aracı kuruma bağlanmak için iki sınıfı uygulayın:

1. `IDataProvider` → gerçek piyasa verisi (ör. aracı kurum WebSocket/REST).
2. `IOrderExecutor` → gerçek emir gönderme/iptal/sorgu.

Kod içinde `# >>> GERÇEK API ENTEGRASYON NOKTASI` yorumları bu yerleri
işaretler. Yeni sınıflarınızı `cmd/main.py` içindeki fabrika fonksiyonlarına
bağlamanız yeterlidir.
