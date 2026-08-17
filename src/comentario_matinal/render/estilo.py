"""Centralized configuration for the market monitor."""

# Unified color palette
COLORS = {
    "positive": "#228B22",
    "negative": "#DC143C",
    "header_bg": "#2E4C59",
    "header_text": "#FFFFFF",
    "row_even": "#FFFFFF",
    "row_odd": "#F0F0F0",
    "text_normal": "#333333",
    "text_positive": "#228B22",
    "title": "#2E4C59",
}

# Rendering
DPI = 150
SAVE_KWARGS = {
    "dpi": DPI,
    "bbox_inches": "tight",
    "facecolor": "white",
    "edgecolor": "none",
}
MONITOR_FIGSIZE = (12, 8)
MONITOR_GRID = (4, 4)

# Font sizes
FONT_SIZES = {
    # Standalone tables
    "title": 18,
    "header": 10,
    "header_cb": 11,
    "cell": 9,
    "cell_cb": 10,
    # Combined tables
    "combined_title": 16,
    "combined_header_eco": 9,
    "combined_header_cb": 10,
    "combined_cell_eco": 8,
    "combined_cell_cb": 9,
    # Monitor panel
    "monitor_column_header": 14,
    "monitor_name": 11,
    "monitor_value": 10,
    "monitor_change": 9,
    "monitor_obs": 8,
}

# Sparkline parameters
SPARKLINE_YLIM = (-0.05, 1.05)
SPARKLINE_LINE_WIDTH = 1.5
SPARKLINE_FILL_ALPHA = 0.3

# Calendar table: ECO columns and widths
ECO_COLUMNS = [
    "PAÍS", "DATA", "HORÁRIO", "EVENTO", "PERÍODO",
    "ESTIMATIVA", "ATUAL", "ANTERIOR", "REVISADO",
]
ECO_COL_WIDTHS = [0.12, 0.10, 0.08, 0.25, 0.08, 0.10, 0.08, 0.10, 0.09]

# Calendar table: CB columns and widths
CB_COLUMNS = ["PAÍS", "DATA", "HORÁRIO", "EVENTO"]
CB_COL_WIDTHS_STANDALONE = [0.15, 0.12, 0.10, 0.61]
CB_COL_WIDTHS_COMBINED = [0.12, 0.10, 0.08, 0.68]

# BQL countries
BQL_COUNTRIES = [
    "US Country", "CA Country", "GB Country", "DE Country",
    "AU Country", "JP Country", "EZ Country", "CN Country",
]

# BQL date range
BQL_DATE_RANGE = "range(-1d,0d)"
