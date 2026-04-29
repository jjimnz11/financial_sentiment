"""
src/utils/logger.py
Logger centralizado con loguru.
Uso: from src.utils.logger import get_logger; logger = get_logger(__name__)
"""

import sys
from pathlib import Path
from loguru import logger as _logger

_configured = False


def get_logger(name: str = "financial_sentiment"):
    """Devuelve un logger con el contexto del módulo dado."""
    global _configured
    if not _configured:
        _setup_logger()
        _configured = True
    return _logger.bind(module=name)


def _setup_logger():
    _logger.remove()  # Elimina el handler por defecto

    # Console — legible en desarrollo
    _logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | "
               "<cyan>{extra[module]}</cyan> — {message}",
        level="DEBUG",
        colorize=True,
    )

    # Archivo rotativo — para producción / scraping continuo
    log_dir = Path(__file__).resolve().parents[2] / "logs"
    log_dir.mkdir(exist_ok=True)
    _logger.add(
        log_dir / "app_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="7 days",
        compression="zip",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {extra[module]} — {message}",
        level="INFO",
    )
