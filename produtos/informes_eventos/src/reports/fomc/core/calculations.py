"""
Calculations and data processing for FOMC analysis.

This module provides functions for processing projection data,
calculating rate paths, and formatting data for display.
"""

import logging
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Economic indicator labels (Portuguese)
INDICATOR_LABELS: dict[str, str] = {
    "Change in real GDP": "Variacao do PIB Real",
    "Unemployment rate": "Taxa de Desemprego",
    "PCE inflation": "Inflacao PCE",
    "Core PCE inflation": "Inflacao PCE Nucleo",
    "Federal funds rate": "Fed Funds Rate",
}

# Short labels for charts
INDICATOR_SHORT_LABELS: dict[str, str] = {
    "Change in real GDP": "PIB",
    "Unemployment rate": "Desemprego",
    "PCE inflation": "PCE",
    "Core PCE inflation": "Core PCE",
    "Federal funds rate": "Fed Funds",
}

# Direção hawkish por indicador
# True = valor maior é hawkish; False = valor menor é hawkish
HAWKISH_WHEN_UP: dict[str, bool] = {
    "Change in real GDP": True,        # PIB maior → mais hawkish (economia forte)
    "Unemployment rate": False,        # Desemprego maior → dovish
    "PCE inflation": True,             # Inflação maior → hawkish
    "Core PCE inflation": True,        # Core PCE maior → hawkish
    "Federal funds rate": True,        # Taxa maior → hawkish
}

# Meses das reuniões SEP
SEP_MONTHS = [3, 6, 9, 12]

# Meses em português (abreviado, para labels)
MESES_PTBR_SHORT: dict[int, str] = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr",
    5: "Mai", 6: "Jun", 7: "Jul", 8: "Ago",
    9: "Set", 10: "Out", 11: "Nov", 12: "Dez",
}

MESES_EN_FULL: dict[int, str] = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December",
}


def _get_year_columns(df: pd.DataFrame) -> list[str]:
    """Extrai colunas de anos do DataFrame (dinâmico, sem hardcode)."""
    return [c for c in df.columns if str(c).isdigit()]


def classify_change_direction(variable: str, change: float) -> str:
    """Classifica a direção de uma mudança como hawkish/dovish/neutral.

    Args:
        variable: Nome do indicador econômico.
        change: Diferença (current - prior).

    Returns:
        "hawkish", "dovish" ou "neutral".
    """
    if abs(change) < 0.001:
        return "neutral"

    is_up = change > 0
    hawkish_when_up = HAWKISH_WHEN_UP.get(variable, True)

    if hawkish_when_up:
        return "hawkish" if is_up else "dovish"
    else:
        return "dovish" if is_up else "hawkish"


def get_prior_sep_meeting_date(current_date: str) -> str | None:
    """Retorna a data da reunião SEP anterior à data fornecida.

    Args:
        current_date: Data no formato YYYYMMDD.

    Returns:
        Data da reunião SEP anterior (YYYYMMDD) ou None.
    """
    from .data_loader import get_fomc_dates

    dt = pd.to_datetime(current_date, format="%Y%m%d")
    current_month = dt.month

    # Encontrar o mês SEP anterior
    prior_sep_months = [m for m in SEP_MONTHS if m < current_month]
    if prior_sep_months:
        target_month = prior_sep_months[-1]
        target_year = dt.year
    else:
        # Último SEP do ano anterior (dezembro)
        target_month = SEP_MONTHS[-1]
        target_year = dt.year - 1

    # Buscar nas datas disponíveis
    fomc_dates = get_fomc_dates()
    for date_str in fomc_dates:
        d = pd.to_datetime(date_str, format="%Y%m%d")
        if d.year == target_year and d.month == target_month:
            return date_str

    return None


def get_prior_meeting_label(prior_date: str) -> str:
    """Gera label para a reunião anterior (ex: 'September projection').

    Args:
        prior_date: Data da reunião anterior (YYYYMMDD).

    Returns:
        Label em inglês (ex: "September projection").
    """
    dt = pd.to_datetime(prior_date, format="%Y%m%d")
    month_name = MESES_EN_FULL.get(dt.month, "")
    return f"{month_name} projection"


def process_dot_plot(
    projection_data: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """Process projection data into dot plot format.

    Takes the parsed projection data and converts it into a format
    suitable for creating a dot plot visualization.

    Args:
        projection_data: Dictionary from parse_projection_table() with
                        'medians' and 'dot_distribution' DataFrames.

    Returns:
        DataFrame with columns: year, rate, count
        Ready for scatter plot visualization.
    """
    medians_df = projection_data.get("medians", pd.DataFrame())

    if medians_df.empty:
        logger.warning("No median data available for dot plot")
        return pd.DataFrame()

    # Extract fed funds rate projections
    ff_row = medians_df[
        medians_df["Variable"].str.contains("federal funds", case=False)
    ]

    if ff_row.empty:
        logger.warning("No federal funds rate in projections")
        return pd.DataFrame()

    # Create dot plot data from medians — dynamic year columns
    records = []
    years = _get_year_columns(medians_df)

    for year in years:
        if year in ff_row.columns:
            rate = ff_row[year].values[0]
            if pd.notna(rate):
                records.append(
                    {
                        "year": year,
                        "rate": float(rate),
                        "count": 1,  # Single dot for median
                        "type": "median",
                    }
                )

    return pd.DataFrame(records)


def calculate_projection_changes(
    current: pd.DataFrame,
    prior: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate changes between two projection vintages.

    Args:
        current: Current meeting's projection medians.
        prior: Prior meeting's projection medians.

    Returns:
        DataFrame with columns: Variable, Current, Prior, Change
    """
    if current.empty or prior.empty:
        return pd.DataFrame()

    # Merge on Variable
    merged = current.merge(
        prior,
        on="Variable",
        suffixes=("_current", "_prior"),
    )

    # Detectar anos dinamicamente
    year_cols = [
        c.replace("_current", "")
        for c in merged.columns
        if c.endswith("_current") and c.replace("_current", "").isdigit()
    ]

    result_records = []
    for _, row in merged.iterrows():
        var = row["Variable"]
        for year in year_cols:
            current_col = f"{year}_current"
            prior_col = f"{year}_prior"

            if current_col in row and prior_col in row:
                current_val = row[current_col]
                prior_val = row[prior_col]

                if pd.notna(current_val) and pd.notna(prior_val):
                    change = current_val - prior_val
                    direction = classify_change_direction(var, change)
                    result_records.append(
                        {
                            "Variable": var,
                            "Year": year,
                            "Current": current_val,
                            "Prior": prior_val,
                            "Change": change,
                            "Direction": direction,
                        }
                    )

    return pd.DataFrame(result_records)


def format_projection_table(
    medians_df: pd.DataFrame,
    include_prior: bool = False,
    prior_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Format projection medians for display in a styled table.

    Args:
        medians_df: DataFrame with median projections.
        include_prior: Whether to include prior meeting's values.
        prior_df: Prior meeting's projection medians.

    Returns:
        Formatted DataFrame ready for styled display.
    """
    if medians_df.empty:
        return pd.DataFrame()

    # Create formatted table
    formatted = medians_df.copy()

    # Rename Variable column to Portuguese
    formatted["Indicador"] = formatted["Variable"].map(
        lambda x: INDICATOR_LABELS.get(x, x)
    )

    # Reorder columns — dynamic years
    available_years = _get_year_columns(formatted)

    result = formatted[["Indicador"] + available_years].copy()

    # Add prior values if requested
    if include_prior and prior_df is not None and not prior_df.empty:
        for year in available_years:
            if year in prior_df.columns:
                # Create prior column with same variable mapping
                prior_mapped = prior_df.set_index("Variable")[year]
                result[f"{year}_Prior"] = formatted["Variable"].map(
                    lambda x: prior_mapped.get(x, np.nan)
                )

    return result


def calculate_rate_path(
    medians_df: pd.DataFrame,
    current_rate: float | None = None,
) -> pd.DataFrame:
    """Calculate the expected rate path from projections.

    Args:
        medians_df: DataFrame with projection medians.
        current_rate: Current federal funds rate (optional).

    Returns:
        DataFrame with year-end rate expectations and implied moves.
    """
    if medians_df.empty:
        return pd.DataFrame()

    # Extract fed funds projections
    ff_row = medians_df[
        medians_df["Variable"].str.contains("federal funds", case=False)
    ]

    if ff_row.empty:
        return pd.DataFrame()

    records = []
    prev_rate = current_rate

    for year in _get_year_columns(medians_df):
        if year in ff_row.columns:
            rate = ff_row[year].values[0]
            if pd.notna(rate):
                move = None
                if prev_rate is not None:
                    move = rate - prev_rate
                    # Convert to basis points
                    move_bps = int(move * 100)

                records.append(
                    {
                        "year": year,
                        "rate": float(rate),
                        "move": move,
                        "move_bps": move_bps if move is not None else None,
                    }
                )
                prev_rate = rate

    return pd.DataFrame(records)


def format_market_reaction_table(
    pre_statement: dict[str, float],
    post_statement: dict[str, float],
    post_presser: dict[str, float] | None = None,
) -> pd.DataFrame:
    """Format market reaction data for display.

    Args:
        pre_statement: Asset prices before statement release.
        post_statement: Asset prices after statement release.
        post_presser: Asset prices after press conference (optional).

    Returns:
        Formatted DataFrame with market reaction.
    """
    assets = ["UST_2Y", "UST_10Y", "SPX", "DXY"]
    asset_labels = {
        "UST_2Y": "UST 2 Anos",
        "UST_10Y": "UST 10 Anos",
        "SPX": "S&P 500",
        "DXY": "DXY",
    }

    records = []
    for asset in assets:
        if asset not in pre_statement or asset not in post_statement:
            continue

        pre = pre_statement[asset]
        post = post_statement[asset]
        change = post - pre

        record = {
            "Ativo": asset_labels.get(asset, asset),
            "Pre-Statement": pre,
            "Pos-Statement": post,
            "Variacao Statement": change,
        }

        if post_presser and asset in post_presser:
            record["Pos-Presser"] = post_presser[asset]
            record["Variacao Presser"] = post_presser[asset] - post

        records.append(record)

    return pd.DataFrame(records)


def calculate_surprise(
    actual: float,
    survey: float,
    indicator: str = "rate",
) -> dict[str, Any]:
    """Calculate the surprise relative to survey expectations.

    Args:
        actual: Actual value released.
        survey: Survey median expectation.
        indicator: Type of indicator ('rate', 'gdp', 'unemployment', 'inflation').

    Returns:
        Dictionary with surprise metrics.
    """
    diff = actual - survey

    # Determine direction based on indicator
    # For rates: higher = hawkish
    # For GDP: higher = stronger
    # For unemployment: higher = weaker
    # For inflation: higher = hawkish

    if indicator in ["unemployment"]:
        # Inverted interpretation
        direction = "fraco" if diff > 0 else "forte" if diff < 0 else "neutro"
    else:
        direction = "forte" if diff > 0 else "fraco" if diff < 0 else "neutro"

    return {
        "actual": actual,
        "survey": survey,
        "surprise": diff,
        "surprise_bps": int(diff * 100) if indicator == "rate" else None,
        "direction": direction,
    }


def get_meeting_summary(
    statement_data: dict[str, Any],
    projection_data: dict[str, pd.DataFrame] | None = None,
) -> dict[str, Any]:
    """Generate a summary of the FOMC meeting.

    Args:
        statement_data: Parsed statement data from parse_statement().
        projection_data: Parsed projection data (optional).

    Returns:
        Dictionary with meeting summary for display.
    """
    summary = {
        "decisao": "",
        "taxa_alvo": "",
        "unanime": True,
        "dissidentes": [],
        "projecoes_resumo": {},
    }

    # Format decision
    decision_map = {
        "hold": "Manutencao",
        "cut": "Corte",
        "hike": "Alta",
    }
    summary["decisao"] = decision_map.get(
        statement_data.get("decision", ""), "N/A"
    )

    # Format target rate
    low = statement_data.get("target_rate_low")
    high = statement_data.get("target_rate_high")
    if low is not None and high is not None:
        summary["taxa_alvo"] = f"{low:.2f}% - {high:.2f}%"

    # Voting
    summary["unanime"] = statement_data.get("unanimous", True)
    summary["dissidentes"] = statement_data.get("dissenters", [])

    # Projections summary
    if projection_data and "medians" in projection_data:
        medians = projection_data["medians"]
        years = _get_year_columns(medians)
        for _, row in medians.iterrows():
            var = row["Variable"]
            short_label = INDICATOR_SHORT_LABELS.get(var, var)
            if years:
                summary["projecoes_resumo"][short_label] = {
                    y: row.get(y) for y in years[:3]
                }

    return summary
