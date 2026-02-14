from __future__ import annotations

import pandas as pd


def calc_drawdown(series: pd.Series) -> pd.Series:
    cummax = series.cummax()
    return (series - cummax) / cummax
