"""PlantaOS configuration package.

Centralizes all application settings, design tokens, building definitions,
and operational thresholds.
"""

from config.settings import settings
from config.theme import (
    ACCENT_BLUE,
    BG_CARD,
    BG_PRIMARY,
    FONT_DATA,
    FONT_PRIMARY,
    STATUS_CRITICAL,
    STATUS_HEALTHY,
    STATUS_WARNING,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)

__all__ = [
    "settings",
    "BG_PRIMARY",
    "BG_CARD",
    "TEXT_PRIMARY",
    "TEXT_SECONDARY",
    "ACCENT_BLUE",
    "STATUS_HEALTHY",
    "STATUS_WARNING",
    "STATUS_CRITICAL",
    "FONT_PRIMARY",
    "FONT_DATA",
]
