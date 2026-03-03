"""PlantaOS design system tokens.

Apple-inspired light UI design system. All visual constants are defined here
and referenced throughout the application. NEVER use hardcoded color values
in components — always import from this module.
"""

# ── Background Colors ─────────────────────────
BG_PRIMARY = "#FAFAFA"
BG_CARD = "#FFFFFF"
BG_HOVER = "#F5F5F7"
BG_SELECTED = "#E8E8ED"
BG_OVERLAY = "rgba(0, 0, 0, 0.4)"

# ── Text Colors ───────────────────────────────
TEXT_PRIMARY = "#1D1D1F"
TEXT_SECONDARY = "#6E6E73"
TEXT_TERTIARY = "#86868B"
TEXT_INVERSE = "#FFFFFF"
TEXT_LINK = "#0071E3"

# ── Accent / Brand ────────────────────────────
ACCENT_GREEN = "#296649"
ACCENT_GREEN_HOVER = "#327A57"
ACCENT_GREEN_LIGHT = "#E8F5EE"
# Legacy alias — components may still reference ACCENT_BLUE
ACCENT_BLUE = ACCENT_GREEN
ACCENT_BLUE_HOVER = ACCENT_GREEN_HOVER
ACCENT_BLUE_LIGHT = ACCENT_GREEN_LIGHT

# ── Status Colors ─────────────────────────────
STATUS_HEALTHY = "#34C759"
STATUS_HEALTHY_LIGHT = "#E8F9EE"
STATUS_WARNING = "#FF9500"
STATUS_WARNING_LIGHT = "#FFF4E6"
STATUS_CRITICAL = "#FF3B30"
STATUS_CRITICAL_LIGHT = "#FFE5E3"
STATUS_INFO = "#5AC8FA"
STATUS_INFO_LIGHT = "#E6F7FE"

# ── Border Colors ─────────────────────────────
BORDER_DEFAULT = "#E5E5EA"
BORDER_LIGHT = "#F2F2F7"
BORDER_FOCUS = ACCENT_BLUE

# ── Surface Tokens ────────────────────────────
CARD_RADIUS = "16px"
CARD_RADIUS_SM = "12px"
CARD_RADIUS_LG = "20px"
CARD_SHADOW = "0 2px 12px rgba(0, 0, 0, 0.08)"
CARD_SHADOW_HOVER = "0 4px 20px rgba(0, 0, 0, 0.12)"
CARD_SHADOW_ELEVATED = "0 8px 32px rgba(0, 0, 0, 0.16)"

# ── Typography ────────────────────────────────
FONT_PRIMARY = "Inter"
FONT_DATA = "JetBrains Mono"
FONT_STACK = (
    f"'{FONT_PRIMARY}', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
)
FONT_DATA_STACK = f"'{FONT_DATA}', 'SF Mono', 'Fira Code', monospace"

WEIGHT_REGULAR = 400
WEIGHT_MEDIUM = 500
WEIGHT_SEMIBOLD = 600

FONT_SIZE_XS = "11px"
FONT_SIZE_SM = "13px"
FONT_SIZE_MD = "15px"
FONT_SIZE_LG = "17px"
FONT_SIZE_XL = "22px"
FONT_SIZE_XXL = "28px"
FONT_SIZE_DISPLAY = "34px"

LINE_HEIGHT_TIGHT = 1.2
LINE_HEIGHT_NORMAL = 1.5
LINE_HEIGHT_RELAXED = 1.7

# ── Spacing (8px grid) ───────────────────────
GRID = 8
SPACING_XS = GRID  # 8px
SPACING_SM = GRID * 2  # 16px
SPACING_MD = GRID * 3  # 24px
SPACING_LG = GRID * 4  # 32px
SPACING_XL = GRID * 5  # 40px
SPACING_XXL = GRID * 6  # 48px

PADDING_CARD = 24
PADDING_PAGE = 32
GAP_ELEMENT = 16
GAP_SECTION = 32

# ── Layout ────────────────────────────────────
SIDEBAR_WIDTH = 240
SIDEBAR_COLLAPSED_WIDTH = 72
HEADER_HEIGHT = 64
CONTENT_MAX_WIDTH = 1440

# ── Animation ─────────────────────────────────
TRANSITION_DEFAULT = "all 300ms ease"
TRANSITION_FAST = "all 150ms ease"
TRANSITION_SLOW = "all 500ms ease"

# ── Chart Defaults (Plotly) ───────────────────
CHART_COLORS = [
    ACCENT_BLUE,
    STATUS_HEALTHY,
    STATUS_WARNING,
    STATUS_CRITICAL,
    STATUS_INFO,
    "#AF52DE",  # Purple
    "#FF2D55",  # Pink
    "#5856D6",  # Indigo
]

CHART_TEMPLATE = {
    "layout": {
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font": {
            "family": FONT_STACK,
            "color": TEXT_PRIMARY,
            "size": 13,
        },
        "title": {
            "font": {
                "size": 17,
                "weight": WEIGHT_SEMIBOLD,
            },
        },
        "xaxis": {
            "showgrid": False,
            "zeroline": False,
            "showline": True,
            "linecolor": BORDER_DEFAULT,
            "linewidth": 1,
        },
        "yaxis": {
            "showgrid": True,
            "gridcolor": BORDER_LIGHT,
            "gridwidth": 1,
            "zeroline": False,
            "showline": False,
        },
        "margin": {"l": 48, "r": 24, "t": 48, "b": 40},
        "hoverlabel": {
            "bgcolor": BG_CARD,
            "bordercolor": BORDER_DEFAULT,
            "font": {"family": FONT_STACK, "size": 13},
        },
        "colorway": CHART_COLORS,
    },
}

# ── Mantine Theme Overrides ──────────────────
MANTINE_THEME = {
    "fontFamily": FONT_STACK,
    "fontFamilyMonospace": FONT_DATA_STACK,
    "primaryColor": "green",
    "colors": {
        "green": [
            "#E8F5EE",
            "#C5E6D3",
            "#9DD4B5",
            "#75C297",
            "#4DAF79",
            ACCENT_GREEN,
            "#215739",
            "#19432C",
            "#112F1F",
            "#091B12",
        ],
    },
    "defaultRadius": "md",
    "spacing": {
        "xs": SPACING_XS,
        "sm": SPACING_SM,
        "md": SPACING_MD,
        "lg": SPACING_LG,
        "xl": SPACING_XL,
    },
}
