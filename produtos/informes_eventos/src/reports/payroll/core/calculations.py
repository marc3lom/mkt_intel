"""
Calculations and transformations for payroll data.

This module provides functions for calculating moving averages,
formatting release summaries, pt-BR date formatting, and summary text generation.
"""

from typing import Any

import pandas as pd

# Mapeamento de meses em pt-BR (sem depender de locale)
MESES_PTBR: dict[int, str] = {
    1: "jan",
    2: "fev",
    3: "mar",
    4: "abr",
    5: "mai",
    6: "jun",
    7: "jul",
    8: "ago",
    9: "set",
    10: "out",
    11: "nov",
    12: "dez",
}

MESES_PTBR_FULL: dict[int, str] = {
    1: "janeiro",
    2: "fevereiro",
    3: "marco",
    4: "abril",
    5: "maio",
    6: "junho",
    7: "julho",
    8: "agosto",
    9: "setembro",
    10: "outubro",
    11: "novembro",
    12: "dezembro",
}


def calculate_moving_averages(
    df: pd.DataFrame,
    column: str = "NFP",
    windows: list[int] | None = None,
) -> pd.DataFrame:
    """Calculate moving averages for a time series column.

    Args:
        df: DataFrame with time series data.
        column: Column name to calculate averages for.
        windows: List of window sizes. Defaults to [3, 6] (months).

    Returns:
        DataFrame with original data plus moving average columns.
    """
    if windows is None:
        windows = [3, 6]

    result = df.copy()

    for window in windows:
        col_name = f"{column}_MA{window}m"
        result[col_name] = result[column].rolling(window=window).mean()

    return result


def format_release_summary(
    release_data: dict[str, dict[str, Any]],
) -> pd.DataFrame:
    """Format release data into a display-ready DataFrame.

    Matches Excel table format with columns:
    Evento, Período, Pesquisa, Atual, Anterior, Revisão

    Args:
        release_data: Dictionary from get_latest_release().

    Returns:
        DataFrame with formatted release summary for display.
    """
    records = []

    indicator_labels = {
        "NFP": "Nonfarm Payrolls",
        "Unemployment": "Unemployment Rate",
        "AHE_MoM": "Average Hourly Earnings MoM",
        "AHE_YoY": "Average Hourly Earnings YoY",
        "LFPR": "Labor Force Participation Rate",
    }

    units = {
        "NFP": "mil",
        "Unemployment": "%",
        "AHE_MoM": "%",
        "AHE_YoY": "%",
        "LFPR": "%",
    }

    # Preserve order matching Excel
    indicator_order = ["NFP", "Unemployment", "AHE_MoM", "AHE_YoY", "LFPR"]

    for indicator in indicator_order:
        if indicator not in release_data:
            continue

        data = release_data[indicator]
        label = indicator_labels.get(indicator, indicator)
        unit = units.get(indicator, "")

        actual = data.get("actual")
        survey = data.get("survey")
        prior = data.get("prior")
        period = data.get("period", "")

        records.append(
            {
                "Evento": label,
                "Periodo": _format_period(period),
                "Pesquisa": _format_value(survey, unit),
                "Atual": _format_value(actual, unit),
                "Anterior": _format_value(prior, unit),
                "Revisao": "",  # Manual field per Excel note
            }
        )

    return pd.DataFrame(records)


def _format_period(period: Any) -> str:
    """Format period string (e.g., '2025-12' -> 'Dec').

    Args:
        period: Period value from Bloomberg.

    Returns:
        Formatted month abbreviation.
    """
    if period is None:
        return "-"

    # Handle various period formats
    period_str = str(period)

    # Try to extract month from date-like strings
    month_map = {
        "01": "Jan",
        "02": "Feb",
        "03": "Mar",
        "04": "Apr",
        "05": "May",
        "06": "Jun",
        "07": "Jul",
        "08": "Aug",
        "09": "Sep",
        "10": "Oct",
        "11": "Nov",
        "12": "Dec",
    }

    # Try YYYY-MM format
    if "-" in period_str and len(period_str) >= 7:
        month = period_str.split("-")[1][:2]
        return month_map.get(month, period_str)

    # Return as-is if already formatted
    return period_str


def style_release_table(df: pd.DataFrame) -> Any:
    """Apply Excel-like styling to release summary table.

    Args:
        df: DataFrame from format_release_summary().

    Returns:
        Styled DataFrame for display.
    """
    # Define styling
    styles = [
        {
            "selector": "th",
            "props": [
                ("background-color", "#2E4C59"),
                ("color", "white"),
                ("font-weight", "bold"),
                ("text-align", "center"),
                ("padding", "8px"),
            ],
        },
        {
            "selector": "td",
            "props": [
                ("text-align", "center"),
                ("padding", "6px"),
            ],
        },
        {
            "selector": "tr:nth-child(even)",
            "props": [
                ("background-color", "#f5f5f5"),
            ],
        },
    ]

    def bold_atual(col: pd.Series) -> list[str]:
        """Make Atual column bold."""
        if col.name == "Atual":
            return ["font-weight: bold"] * len(col)
        return [""] * len(col)

    return df.style.set_table_styles(styles).apply(bold_atual, axis=0).hide(axis="index")


def _format_value(value: Any, unit: str) -> str:
    """Format a numeric value with unit.

    Args:
        value: Numeric value to format.
        unit: Unit string (%, mil, etc.).

    Returns:
        Formatted string.
    """
    if value is None:
        return "-"

    if unit == "mil":
        return f"{value:.0f}k"
    elif unit == "%":
        return f"{value:.1f}%"
    else:
        return f"{value}"


def _format_surprise(value: Any, unit: str) -> str:
    """Format surprise value with sign and color indicator.

    Args:
        value: Surprise value (actual - survey).
        unit: Unit string.

    Returns:
        Formatted string with sign.
    """
    if value is None:
        return "-"

    sign = "+" if value > 0 else ""

    if unit == "mil":
        return f"{sign}{value:.0f}k"
    elif unit == "%":
        return f"{sign}{value:.1f}%"
    else:
        return f"{sign}{value}"


def calculate_period_stats(df: pd.DataFrame, column: str = "NFP") -> dict[str, float]:
    """Calculate summary statistics for a period.

    Args:
        df: DataFrame with time series data.
        column: Column to calculate stats for.

    Returns:
        Dictionary with mean, std, min, max, latest values.
    """
    series = df[column].dropna()

    return {
        "mean": series.mean(),
        "std": series.std(),
        "min": series.min(),
        "max": series.max(),
        "latest": series.iloc[-1] if len(series) > 0 else None,
        "count": len(series),
    }


def get_trend_assessment(df: pd.DataFrame, column: str = "NFP") -> str:
    """Assess the trend direction for an indicator.

    Args:
        df: DataFrame with time series data.
        column: Column to assess.

    Returns:
        Trend description string.
    """
    series = df[column].dropna()

    if len(series) < 3:
        return "Dados insuficientes"

    # Compare 3-month average to 6-month average
    ma3 = series.tail(3).mean()
    ma6 = series.tail(6).mean()

    if ma3 > ma6 * 1.1:
        return "Acelerando"
    elif ma3 < ma6 * 0.9:
        return "Desacelerando"
    else:
        return "Estavel"


def format_date_ptbr(date: Any, fmt: str = "%b-%y") -> str:
    """Format a date using pt-BR month abbreviations.

    Supports format tokens: %b (abrev.), %B (full), %y (2-digit year), %Y (4-digit year),
    %m (zero-padded month), %d (zero-padded day).

    Args:
        date: Date-like object (datetime, Timestamp, string).
        fmt: Format string using %-style tokens.

    Returns:
        Formatted date string in pt-BR.
    """
    if isinstance(date, str):
        date = pd.to_datetime(date)

    result = fmt
    result = result.replace("%B", MESES_PTBR_FULL.get(date.month, ""))
    result = result.replace("%b", MESES_PTBR.get(date.month, ""))
    result = result.replace("%Y", str(date.year))
    result = result.replace("%y", f"{date.year % 100:02d}")
    result = result.replace("%m", f"{date.month:02d}")
    result = result.replace("%d", f"{date.day:02d}")
    return result


def generate_summary_text(
    release_data: dict[str, dict[str, Any]],
    industry_data: pd.DataFrame | None = None,
) -> str:
    """Generate a narrative summary paragraph in pt-BR for the Word report.

    Args:
        release_data: Dictionary from get_latest_release().
        industry_data: Optional industry breakdown DataFrame.

    Returns:
        Summary text paragraph in Portuguese.
    """
    nfp = release_data.get("NFP", {})
    unemp = release_data.get("Unemployment", {})
    ahe_mom = release_data.get("AHE_MoM", {})
    ahe_yoy = release_data.get("AHE_YoY", {})

    nfp_actual = nfp.get("actual")
    nfp_survey = nfp.get("survey")
    nfp_prior = nfp.get("prior")
    unemp_actual = unemp.get("actual")
    ahe_mom_actual = ahe_mom.get("actual")
    ahe_yoy_actual = ahe_yoy.get("actual")
    period = nfp.get("period", "")

    # Determine month name
    month_name = period
    if isinstance(period, str) and "-" in period:
        try:
            dt = pd.to_datetime(period)
            month_name = format_date_ptbr(dt, "%B/%Y")
        except Exception:
            pass

    parts = []

    # NFP headline
    if nfp_actual is not None:
        direction = "acima" if (nfp_survey and nfp_actual > nfp_survey) else "abaixo"
        if nfp_survey and abs(nfp_actual - nfp_survey) < 10:
            direction = "em linha com"
        parts.append(
            f"A economia americana criou {nfp_actual:.0f} mil empregos em {month_name}, "
            f"{direction} da expectativa de {nfp_survey:.0f} mil"
            if nfp_survey
            else f"A economia americana criou {nfp_actual:.0f} mil empregos em {month_name}"
        )
        if nfp_prior is not None:
            parts[-1] += f" (anterior: {nfp_prior:.0f} mil)."
        else:
            parts[-1] += "."

    # Unemployment
    if unemp_actual is not None:
        parts.append(f"A taxa de desemprego ficou em {unemp_actual:.1f}%.")

    # Wages
    if ahe_mom_actual is not None and ahe_yoy_actual is not None:
        parts.append(
            f"Os salarios por hora avancaram {ahe_mom_actual:.1f}% no mes "
            f"e {ahe_yoy_actual:.1f}% na comparacao anual."
        )

    # Top industries
    if industry_data is not None and len(industry_data) > 0:
        top = industry_data[
            ~industry_data["industry"].str.contains("Total|private|Goods|service", case=False)
        ].nlargest(3, "current_month")
        if len(top) > 0:
            sectors = ", ".join(
                f"{row['industry']} ({row['current_month']:+.0f}k)" for _, row in top.iterrows()
            )
            parts.append(f"Os setores que mais contribuiram foram: {sectors}.")

    return " ".join(parts)
