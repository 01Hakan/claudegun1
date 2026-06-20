"""
Logging & Monitoring Katmanı
============================

Tüm modüllerin ortak kullandığı yapılandırılmış loglayıcı.

Log formatı:  ``ZAMAN_DAMGASI | SEVİYE | MODÜL | MESAJ``

Kullanım:
    >>> from bistrobot.logging_utils.logger import get_logger
    >>> log = get_logger("strategy")
    >>> log.info("AKBNK.E için long sinyali üretildi")
"""

from __future__ import annotations

import logging
import os
import sys

# Robot içinde kullanılan seviye isimleri ile stdlib logging eşlemesi.
_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARN": logging.WARNING,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
}

# Kök logger adı; tüm alt modüller bunun çocuğu olur ("bistrobot.strategy" gibi).
_ROOT_NAME = "bistrobot"
_CONFIGURED = False


def configure_logging(level: str = "INFO",
                      to_file: bool = False,
                      file_path: str = "logs/robot.log") -> None:
    """Loglamayı bir kez yapılandırır (idempotent).

    Args:
        level: DEBUG | INFO | WARN | ERROR
        to_file: True ise ayrıca dosyaya yazar.
        file_path: Dosya yolu (klasör yoksa oluşturulur).
    """
    global _CONFIGURED
    root = logging.getLogger(_ROOT_NAME)
    root.setLevel(_LEVELS.get(level.upper(), logging.INFO))

    # Tekrar yapılandırmada eski handler'ları temizle (test/yeniden başlatma).
    root.handlers.clear()

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-5s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Konsol handler'ı.
    console = logging.StreamHandler(stream=sys.stdout)
    console.setFormatter(fmt)
    root.addHandler(console)

    # Opsiyonel dosya handler'ı.
    if to_file:
        os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)
        fh = logging.FileHandler(file_path, encoding="utf-8")
        fh.setFormatter(fmt)
        root.addHandler(fh)

    # Üst loggerlara yayılımı kapat (çift log önlemi).
    root.propagate = False
    _CONFIGURED = True


def get_logger(module: str) -> logging.Logger:
    """Belirli bir modül için alt logger döndürür.

    Henüz yapılandırma yapılmadıysa makul bir varsayılan uygular.
    """
    if not _CONFIGURED:
        configure_logging()
    return logging.getLogger(f"{_ROOT_NAME}.{module}")
