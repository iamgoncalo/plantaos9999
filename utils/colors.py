"""Color interpolation and zone-to-color mapping.

Maps Building Health scores (0-100) and comfort metrics to the
design system color palette for consistent visualization.
"""

from __future__ import annotations

from config.theme import (
    STATUS_CRITICAL,
    STATUS_HEALTHY,
    STATUS_WARNING,
    TEXT_TERTIARY,
)

# Health score color stops: (score_threshold, hex_color)
_HEALTH_STOPS: list[tuple[float, str]] = [
    (0.0, STATUS_CRITICAL),  # #FF3B30
    (30.0, STATUS_WARNING),  # #FF9500
    (60.0, "#FFD60A"),  # Apple yellow
    (80.0, STATUS_HEALTHY),  # #34C759
    (100.0, STATUS_HEALTHY),  # #34C759
]


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert a hex color string to RGB tuple.

    Args:
        hex_color: Color string like '#FF3B30'.

    Returns:
        Tuple of (red, green, blue) integers 0-255.
    """
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert RGB values to hex color string.

    Args:
        r: Red component 0-255.
        g: Green component 0-255.
        b: Blue component 0-255.

    Returns:
        Hex color string like '#FF3B30'.
    """
    return f"#{r:02X}{g:02X}{b:02X}"


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
    if color_scale is None:
        color_scale = [STATUS_CRITICAL, STATUS_WARNING, STATUS_HEALTHY]
    if max_val == min_val:
        return color_scale[-1]

    t = max(0.0, min(1.0, (value - min_val) / (max_val - min_val)))
    n = len(color_scale) - 1
    idx = t * n
    lower = int(idx)
    upper = min(lower + 1, n)
    frac = idx - lower

    r1, g1, b1 = hex_to_rgb(color_scale[lower])
    r2, g2, b2 = hex_to_rgb(color_scale[upper])
    r = int(r1 + (r2 - r1) * frac)
    g = int(g1 + (g2 - g1) * frac)
    b = int(b1 + (b2 - b1) * frac)
    return rgb_to_hex(r, g, b)


def zone_health_to_color(score: float) -> str:
    """Map a Building Health score (0-100) to a status color.

    Args:
        score: Zone health score from 0 (poor) to 100 (excellent).

    Returns:
        Hex color string from the zone status palette.
    """
    score = max(0.0, min(100.0, score))

    for i in range(len(_HEALTH_STOPS) - 1):
        low_score, low_color = _HEALTH_STOPS[i]
        high_score, high_color = _HEALTH_STOPS[i + 1]
        if score <= high_score:
            if high_score == low_score:
                t = 0.0
            else:
                t = (score - low_score) / (high_score - low_score)
            r1, g1, b1 = hex_to_rgb(low_color)
            r2, g2, b2 = hex_to_rgb(high_color)
            r = int(r1 + (r2 - r1) * t)
            g = int(g1 + (g2 - g1) * t)
            b = int(b1 + (b2 - b1) * t)
            return rgb_to_hex(r, g, b)

    return STATUS_HEALTHY


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
