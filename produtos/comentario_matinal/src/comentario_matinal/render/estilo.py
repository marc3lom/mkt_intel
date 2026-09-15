"""Configuração centralizada do painel de mercado."""

# Paleta de cores unificada
CORES = {
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

# Renderização
DPI = 150
SAVE_KWARGS = {
    "dpi": DPI,
    "bbox_inches": "tight",
    "facecolor": "white",
    "edgecolor": "none",
}
MONITOR_FIGSIZE = (12, 8)
MONITOR_GRID = (4, 4)

# Tamanhos de fonte
FONTES = {
    # Tabelas avulsas
    "title": 18,
    "header": 10,
    "header_cb": 11,
    "cell": 9,
    "cell_cb": 10,
    # Tabelas combinadas
    "combined_title": 16,
    "combined_header_eco": 9,
    "combined_header_cb": 10,
    "combined_cell_eco": 8,
    "combined_cell_cb": 9,
    # Painel de monitoramento
    "monitor_column_header": 14,
    "monitor_name": 11,
    "monitor_value": 10,
    "monitor_change": 9,
    "monitor_obs": 8,
}

# Parâmetros do sparkline
SPARKLINE_YLIM = (-0.05, 1.05)
SPARKLINE_LINE_WIDTH = 1.5
SPARKLINE_FILL_ALPHA = 0.3
