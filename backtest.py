import pandas as pd
import numpy as np
from scipy import stats

DATA_FILE = "metaux_daily_data.csv"

HORIZONS = [1, 5, 10, 20, 60]
TRANSACTION_COST_PCT = 0.05
P_VALUE_THRESHOLD = 0.05
N_BOOTSTRAP = 1_000
MIN_OCC_PER_PERIOD = 10
FRESH_DATA_DAYS = 90

SIGNALS = [
    {
        "name": "Flux GLD — entrées fortes (proxy volume)",
        "column": "gld_etf_flow_signal_zscore",
        "fallback_col": "gld_flow_tonnes_5j_zscore",
        "condition": lambda s: s > 1.5,
        "target_metal": "gold_front_close",
        "direction": 1,
    },
    {
        "name": "Flux GLD — sorties fortes (proxy volume)",
        "column": "gld_etf_flow_signal_zscore",
        "fallback_col": "gld_flow_tonnes_5j_zscore",
        "condition": lambda s: s < -1.5,
        "target_metal": "gold_front_close",
        "direction": -1,
    },
    {
        "name": "Taux réels US — niveau bas (favorable or)",
        "column": "real_yield_10y_zscore",
        "condition": lambda s: s < -1.5,
        "target_metal": "gold_front_close",
        "direction": 1,
    },
    {
        "name": "DXY — spike haussier (négatif pour or)",
        "column": "dxy_close_zscore",
        "condition": lambda s: s > 2.0,
        "target_metal": "gold_front_close",
        "direction": -1,
    },
    {
        "name": "Vol implicite or en spike (GVZ)",
        "column": "gvz_close_zscore",
        "condition": lambda s: s > 1.5,
        "target_metal": "gold_front_close",
        "direction": 1,
    },
    {
        "name": "Ratio Or/Argent — extrême haut (argent sous-évalué)",
        "column": "gold_silver_ratio_zscore",
        "condition": lambda s: s > 2.0,
        "target_metal": "silver_front_close",
        "direction": 1,
    },
    {
        "name": "Ratio Or/Argent — extrême bas (argent sur-évalué)",
        "column": "gold_silver_ratio_zscore",
        "condition": lambda s: s < -2.0,
        "target_metal": "silver_front_close",
        "direction": -1,
    },
    {
        "name": "Ratio Cuivre/Or — extrême haut (mean-reversion short cuivre)",
        "column": "copper_gold_ratio_zscore",
        "condition": lambda s: s > 2.0,
        "target_metal": "copper_front_close",
        "direction": -1,
    },
    {
        "name": "Ratio Cuivre/Or — extrême bas (mean-reversion long cuivre)",
        "column": "copper_gold_ratio_zscore",
        "condition": lambda s: s < -2.0,
        "target_metal": "copper_front_close",
        "direction": 1,
    },
    {
        "name": "Production industrielle — expansion forte (long cuivre)",
        "column": "industrial_production_zscore",
        "condition": lambda s: s > 1.5,
        "target_metal": "copper_front_close",
        "direction": 1,
    },
    {
        "name": "Treasury 10Y — spike haussier (négatif pour or)",
        "column": "treasury_10y_zscore",
        "condition": lambda s: s > 2.0,
        "target_metal": "gold_front_close",
        "direction": -1,
    },
    {
        "name": "COT Or — positionnement spéculatif extrême haut (mean-reversion short)",
        "column": "cot_gold_net_spec_zscore",
        "condition": lambda s: s > 2.0,
        "target_metal": "gold_front_close",
        "direction": -1,
    },
    {
        "name": "COT Or — positionnement spéculatif extrême bas (contrarian long)",
        "column": "cot_gold_net_spec_zscore",
        "condition": lambda s: s < -2.0,
        "target_metal": "gold_front_close",
        "direction": 1,
    },
]


def _resolve_column(df: pd.DataFrame, signal: dict) -> str | None:
    if signal["column"] in df.columns:
        return signal["column"]
    fallback = signal.get("fallback_col")
    if fallback and fallback in df.columns:
        return fallback
    return None


def compute_forward_returns(df: pd.DataFrame, price_col: str, horizon: int) -> pd.Series:
    return (df[price_col].shift(-horizon) / df[price_col] - 1) * 100


def bootstrap_ci(data: np.ndarray, n_resamples: int = N_BOOTSTRAP, confidence: float = 0.95) -> tuple[float, float]:
    if len(data) < 2:
        return (np.nan, np.nan)
    rng = np.random.default_rng(42)
    means = [rng.choice(data, size=len(data), replace=True).mean() for _ in range(n_resamples)]
    alpha = (1 - confidence) / 2
    return (float(np.quantile(means, alpha)), float(np.quantile(means, 1 - alpha)))


def compute_max_drawdown(returns_pct: np.ndarray) -> float:
    if len(returns_pct) == 0:
        return np.nan
    cum = (1 + returns_pct / 100).cumprod()
    running_max = np.maximum.accumulate(cum)
    drawdowns = (cum - running_max) / running_max
    return float(drawdowns.min() * 100)


def split_fresh_and_backtest(df: pd.DataFrame, fresh_days: int = FRESH_DATA_DAYS) -> tuple[pd.DataFrame, pd.DataFrame]:
    fresh_df = df.copy()
    backtest_df = df.copy()
    return fresh_df, backtest_df


def test_signal(df: pd.DataFrame, signal: dict, horizon: int) -> dict:
    col = _resolve_column(df, signal)
    price_col = signal["target_metal"]
    direction = signal.get("direction", 1)

    base = {
        "signal": signal["name"],
        "colonne_signal": col or signal["column"],
        "metal": price_col,
        "horizon_j": horizon,
        "direction": "Long" if direction == 1 else "Short",
    }

    if col is None or price_col not in df.columns:
        return {**base, "erreur": "colonne signal absente du CSV", "verdict": "⛔ Données manquantes"}
    if df[col].isna().all():
        return {**base, "erreur": "colonne signal entièrement vide", "verdict": "⛔ Données manquantes"}

    raw_fwd_ret = compute_forward_returns(df, price_col, horizon)
    fwd_ret = direction * raw_fwd_ret

    cond_mask = signal["condition"](df[col])
    mask = cond_mask & fwd_ret.notna() & df[col].notna()

    baseline_mask = ~cond_mask & fwd_ret.notna() & df[col].notna()
    baseline_returns = fwd_ret[baseline_mask].values
    baseline_mean = float(baseline_returns.mean()) if len(baseline_returns) > 0 else np.nan

    n_signal = int(mask.sum())
    if n_signal == 0:
        return {
            **base,
            "occurrences": 0,
            "rendement_brut_%": None,
            "rendement_net_%": None,
            "rendement_baseline_%": round(baseline_mean, 4) if not np.isnan(baseline_mean) else None,
            "verdict": "⚠️ Aucune occurrence",
        }

    signal_returns = fwd_ret[mask].values
    signal_mean = float(signal_returns.mean())
    net_return = signal_mean - TRANSACTION_COST_PCT

    if len(baseline_returns) >= 2:
        t_stat, p_value = stats.ttest_ind(signal_returns, baseline_returns, equal_var=False)
    else:
        t_stat, p_value = np.nan, np.nan

    ci_low, ci_high = bootstrap_ci(signal_returns)

    signal_std = float(signal_returns.std(ddof=1)) if len(signal_returns) >= 2 else np.nan
    if not np.isnan(signal_std) and signal_std > 0 and not np.isnan(baseline_mean):
        information_ratio = round((signal_mean - baseline_mean) / signal_std, 4)
    else:
        information_ratio = np.nan

    hit_rate = float((signal_returns > 0).mean()) * 100
    max_dd = compute_max_drawdown(signal_returns)

    n = len(df)
    t1, t2 = n // 3, 2 * n // 3
    full_fwd = fwd_ret
    periods = [
        (df.iloc[:t1],  full_fwd.iloc[:t1]),
        (df.iloc[t1:t2], full_fwd.iloc[t1:t2]),
        (df.iloc[t2:],  full_fwd.iloc[t2:]),
    ]

    period_means = []
    period_occs  = []
    for pdf, pfwd in periods:
        pmask = signal["condition"](pdf[col]) & pfwd.notna() & pdf[col].notna()
        occ   = int(pmask.sum())
        period_occs.append(occ)
        if occ >= MIN_OCC_PER_PERIOD:
            period_means.append(float(pfwd[pmask].mean()))
        else:
            period_means.append(np.nan)

    valid_means = [m for m in period_means if not np.isnan(m)]
    has_enough  = all(o >= MIN_OCC_PER_PERIOD for o in period_occs)
    same_sign   = (
        len(valid_means) == 3
        and len(set(np.sign(valid_means))) == 1
        and np.sign(valid_means[0]) == np.sign(signal_mean)
    )
    robust = bool(has_enough and same_sign)

    sig_ok  = not np.isnan(p_value) and p_value < P_VALUE_THRESHOLD
    ci_positive = not np.isnan(ci_low) and ci_low > 0
    beats_baseline = net_return > baseline_mean * 1.5 if not np.isnan(baseline_mean) else False

    if not has_enough:
        verdict = "⚠️ Occurrences insuffisantes par sous-période"
    elif not sig_ok:
        verdict = "❌ Non significatif (p > 5 %)"
    elif not robust:
        verdict = "❌ Non robuste sur les 3 sous-périodes"
    elif robust and sig_ok and beats_baseline and ci_positive:
        verdict = "✅ Signal institutionnel — priorité haute"
    elif robust and sig_ok:
        verdict = "🔶 Robuste mais faible alpha — à surveiller"
    else:
        verdict = "❌ Non robuste"

    return {
        "signal": signal["name"],
        "colonne_signal": col,
        "metal": price_col,
        "horizon_j": horizon,
        "direction": "Long" if direction == 1 else "Short",
        "occurrences": n_signal,
        "rendement_brut_%": round(signal_mean, 4),
        "rendement_net_%": round(net_return, 4),
        "rendement_baseline_%": round(baseline_mean, 4) if not np.isnan(baseline_mean) else None,
        "p_value": round(p_value, 4) if not np.isnan(p_value) else None,
        "t_stat": round(t_stat, 4) if not np.isnan(t_stat) else None,
        "ic_95_bas_%": round(ci_low, 4) if not np.isnan(ci_low) else None,
        "ic_95_haut_%": round(ci_high, 4) if not np.isnan(ci_high) else None,
        "ratio_information": information_ratio,
        "taux_succes_%": round(hit_rate, 2),
        "max_drawdown_%": round(max_dd, 4) if not np.isnan(max_dd) else None,
        "occurrences_p1": period_occs[0],
        "rendement_p1_%": round(period_means[0], 4) if not np.isnan(period_means[0]) else None,
        "occurrences_p2": period_occs[1],
        "rendement_p2_%": round(period_means[1], 4) if not np.isnan(period_means[1]) else None,
        "occurrences_p3": period_occs[2],
        "rendement_p3_%": round(period_means[2], 4) if not np.isnan(period_means[2]) else None,
        "robuste_3_periodes": robust,
        "verdict": verdict,
    }


def run_backtest(data_file: str = DATA_FILE) -> pd.DataFrame:
    _COMPAT_RENAME = {
        "DFII10": "real_yield_10y",
        "T10YIE": "breakeven_10y",
        "DGS10":  "treasury_10y",
        "INDPRO": "industrial_production",
    }

    df = pd.read_csv(data_file, index_col=0, parse_dates=True).sort_index()
    df = df.rename(columns={k: v for k, v in _COMPAT_RENAME.items() if k in df.columns})

    z_targets = [
        ("real_yield_10y", "real_yield_10y_zscore"),
        ("treasury_10y", "treasury_10y_zscore"),
        ("industrial_production", "industrial_production_zscore"),
        ("gld_etf_flow_signal", "gld_etf_flow_signal_zscore"),
        ("cot_gold_net_spec", "cot_gold_net_spec_zscore"),
    ]
    for src, dst in z_targets:
        if src in df.columns and dst not in df.columns:
            roll_m = df[src].rolling(60, min_periods=15).mean()
            roll_s = df[src].rolling(60, min_periods=15).std()
            df[dst] = (df[src] - roll_m) / roll_s

    fresh_df, backtest_df = split_fresh_and_backtest(df, FRESH_DATA_DAYS)
    fresh_df.to_csv("fresh_daily_snapshot.csv", index=True)

    results = []
    for signal in SIGNALS:
        for horizon in HORIZONS:
            results.append(test_signal(backtest_df, signal, horizon))

    results_df = pd.DataFrame(results)
    results_df.to_csv("backtest_results.csv", index=False)
    return results_df


def print_results(results: pd.DataFrame) -> None:
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", None)
    pd.set_option("display.float_format", "{:.4f}".format)

    print("\n" + "=" * 80)
    print("  BACKTEST QUANTITATIF — CDG CAPITAL GESTION")
    print("=" * 80)

    display_cols = [
        "signal", "horizon_j", "direction", "occurrences",
        "rendement_brut_%", "rendement_net_%", "rendement_baseline_%",
        "p_value", "ratio_information", "taux_succes_%",
        "robuste_3_periodes", "verdict",
    ]
    display_cols = [c for c in display_cols if c in results.columns]
    disp = results[display_cols].copy()
    if "verdict" in disp.columns:
        disp["verdict"] = disp["verdict"].str.replace(
            r"[\U00010000-\U0010ffff\u2600-\u27BF\u2B00-\u2BFF\uFE00-\uFEFF]",
            "", regex=True).str.strip()
    print(disp.to_string(index=False))

    print("\n" + "=" * 80)
    print("  SIGNAUX PRIORITAIRES")
    print("=" * 80)
    prioritaires = results[results["verdict"].str.contains("priorité haute", na=False)]
    if prioritaires.empty:
        print("  Aucun signal prioritaire détecté.")
    else:
        print(prioritaires[display_cols].to_string(index=False))

    print(f"\nResultats sauvegardes -> backtest_results.csv")


if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("Execution du backtest...\n")
    results = run_backtest()
    print_results(results)
