"""Color interpolation and zone-to-color mapping.

Maps Freedom Index scores (0-100) and comfort metrics to the
design system color palette for consistent visualization.
"""

from __future__ import annotations

from config.theme import (
    STATUS_CRITICAL,
    STATUS_HEALTHY,
    STATUS_WARNING,
    TEXT_TERTIARY,
)


def interpolate_color(
    value: float,
    min_val: float,
    max_val: float,
    color_scale: list[str] | None = None,
) -> str:
    """Interpolate between colors on a scale based on a value.

    Args:
        value: The current metric value.
        min_val: Minimum of the scale range.
        max_val: Maximum of the scale range.
        color_scale: List of hex color strings. Defaults to theme heatmap.

    Returns:
        Hex color string interpolated from the scale.
    """
    ...


def zone_health_to_color(score: float) -> str:
    """Map a Freedom Index score (0-100) to a status color.

    Args:
        score: Zone health score from 0 (poor) to 100 (excellent).

    Returns:
        Hex color string from the zone status palette.
    """
    ...


def status_color(status: str) -> str:
    """Get the color for a status level.

    Args:
        status: Status string ('healthy', 'warning', 'critical', 'unknown').

    Returns:
        Hex color string from the design system.
    """
    colors = {
        "healthy": STATUS_HEALTHY,
        "optimal": STATUS_HEALTHY,
        "warning": STATUS_WARNING,
        "acceptable": STATUS_WARNING,
        "critical": STATUS_CRITICAL,
        "unknown": TEXT_TERTIARY,
    }
    return colors.get(status, TEXT_TERTIARY)


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert a hex color string to RGB tuple.

    Args:
        hex_color: Color string like '#FF3B30'.

    Returns:
        Tuple of (red, green, blue) integers 0-255.
    """
    ...


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert RGB values to hex color string.

    Args:
        r: Red component 0-255.
        g: Green component 0-255.
        b: Blue component 0-255.

    Returns:
        Hex color string like '#FF3B30'.
    """
    ...
