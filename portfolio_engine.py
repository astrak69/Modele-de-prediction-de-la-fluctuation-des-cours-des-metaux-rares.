import math
import numpy as np
import pandas as pd
from datetime import datetime
from scipy import stats

DATA_FILE = "metaux_daily_data.csv"

BENCHMARK_WEIGHTS = {
    "gold": 0.49,
    "silver": 0.16,
    "copper": 0.27,
    "cash": 0.08,
}

TACTICAL_CONSTRAINTS = {
    "gold": {"min": 0.30, "max": 0.65, "max_tilt": 0.15},
    "silver": {"min": 0.08, "max": 0.25, "max_tilt": 0.08},
    "copper": {"min": 0.15, "max": 0.40, "max_tilt": 0.10},
    "cash": {"min": 0.02, "max": 0.25},
}

REBALANCE_COST_BPS = 0.0005
RISK_FREE_RATE_ANNUAL = 0.03

SIGNAL_RULES = {
    "gold": [
        {"col": "gld_etf_flow_signal_zscore", "cond": lambda s: s > 1.5, "dir": +1.0, "weight": 1.5, "name": "Flux GLD Inflows"},
        {"col": "gld_etf_flow_signal_zscore", "cond": lambda s: s < -1.5, "dir": -1.0, "weight": 1.5, "name": "Flux GLD Outflows"},
        {"col": "real_yield_10y_zscore", "cond": lambda s: s < -1.5, "dir": +1.0, "weight": 2.0, "name": "Taux Réels Bas"},
        {"col": "real_yield_10y_zscore", "cond": lambda s: s > 1.5, "dir": -1.0, "weight": 1.5, "name": "Taux Réels Hauts"},
        {"col": "dxy_close_zscore", "cond": lambda s: s > 2.0, "dir": -1.0, "weight": 1.5, "name": "DXY Spike Haussier"},
        {"col": "dxy_close_zscore", "cond": lambda s: s < -1.5, "dir": +1.0, "weight": 1.0, "name": "DXY Faible"},
        {"col": "gvz_close_zscore", "cond": lambda s: s > 1.5, "dir": +1.0, "weight": 1.0, "name": "GVZ Spike"},
        {"col": "treasury_10y_zscore", "cond": lambda s: s > 2.0, "dir": -1.0, "weight": 1.0, "name": "T-Notes 10Y Spike"},
        {"col": "cot_gold_net_spec_zscore", "cond": lambda s: s > 2.0, "dir": -1.0, "weight": 1.2, "name": "COT Or Surachat"},
        {"col": "cot_gold_net_spec_zscore", "cond": lambda s: s < -2.0, "dir": +1.0, "weight": 1.2, "name": "COT Or Capitulation"},
    ],
    "silver": [
        {"col": "gold_silver_ratio_zscore", "cond": lambda s: s > 2.0, "dir": +1.0, "weight": 2.0, "name": "Ratio Or/Argent Haut"},
        {"col": "gold_silver_ratio_zscore", "cond": lambda s: s < -2.0, "dir": -1.0, "weight": 1.5, "name": "Ratio Or/Argent Bas"},
        {"col": "slv_etf_flow_signal", "cond": lambda s: s > 1.5, "dir": +1.0, "weight": 1.0, "name": "SLV Volume Inflows"},
        {"col": "slv_etf_flow_signal", "cond": lambda s: s < -1.5, "dir": -1.0, "weight": 1.0, "name": "SLV Volume Outflows"},
    ],
    "copper": [
        {"col": "copper_gold_ratio_zscore", "cond": lambda s: s > 2.0, "dir": -1.0, "weight": 1.5, "name": "Ratio Cuivre/Or Haut"},
        {"col": "copper_gold_ratio_zscore", "cond": lambda s: s < -2.0, "dir": +1.0, "weight": 1.5, "name": "Ratio Cuivre/Or Bas"},
        {"col": "industrial_production_zscore", "cond": lambda s: s > 1.5, "dir": +1.0, "weight": 2.0, "name": "Production Industrielle Forte"},
        {"col": "industrial_production_zscore", "cond": lambda s: s < -1.5, "dir": -1.0, "weight": 1.5, "name": "Production Industrielle Faible"},
        {"col": "cper_etf_flow_signal", "cond": lambda s: s > 1.5, "dir": +1.0, "weight": 1.0, "name": "CPER Inflows"},
    ],
}


def load_and_enrich_data(data_file: str = DATA_FILE) -> pd.DataFrame:
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

    df["gold_ret"] = df["gold_front_close"].pct_change().fillna(0)
    df["silver_ret"] = df["silver_front_close"].pct_change().fillna(0)
    df["copper_ret"] = df["copper_front_close"].pct_change().fillna(0)
    df["cash_ret"] = (1 + RISK_FREE_RATE_ANNUAL) ** (1 / 252) - 1

    return df


def compute_daily_scores_and_weights(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    
    for metal, rules in SIGNAL_RULES.items():
        score_series = pd.Series(0.0, index=out.index)
        weight_sum_series = pd.Series(0.0, index=out.index)
        
        for r in rules:
            col = r["col"]
            if col in out.columns:
                valid_mask = out[col].notna()
                act_mask = valid_mask & r["cond"](out[col])
                contrib = act_mask.astype(float) * r["dir"] * r["weight"]
                score_series += contrib
                weight_sum_series += r["weight"]
        
        max_possible_weight = max(sum(r["weight"] for r in rules), 1.0)
        raw_score = score_series / (weight_sum_series.replace(0, np.nan).fillna(max_possible_weight))
        out[f"score_{metal}"] = np.clip(raw_score * 2.0, -1.0, 1.0)

    w_gold = []
    w_silver = []
    w_copper = []
    w_cash = []

    for idx, row in out.iterrows():
        sg = row.get("score_gold", 0.0)
        ss = row.get("score_silver", 0.0)
        sc = row.get("score_copper", 0.0)
        
        if pd.isna(sg): sg = 0.0
        if pd.isna(ss): ss = 0.0
        if pd.isna(sc): sc = 0.0

        tilt_g = sg * TACTICAL_CONSTRAINTS["gold"]["max_tilt"]
        tilt_s = ss * TACTICAL_CONSTRAINTS["silver"]["max_tilt"]
        tilt_c = sc * TACTICAL_CONSTRAINTS["copper"]["max_tilt"]

        wg = BENCHMARK_WEIGHTS["gold"] + tilt_g
        ws = BENCHMARK_WEIGHTS["silver"] + tilt_s
        wc = BENCHMARK_WEIGHTS["copper"] + tilt_c

        wg = np.clip(wg, TACTICAL_CONSTRAINTS["gold"]["min"], TACTICAL_CONSTRAINTS["gold"]["max"])
        ws = np.clip(ws, TACTICAL_CONSTRAINTS["silver"]["min"], TACTICAL_CONSTRAINTS["silver"]["max"])
        wc = np.clip(wc, TACTICAL_CONSTRAINTS["copper"]["min"], TACTICAL_CONSTRAINTS["copper"]["max"])

        total_metals = wg + ws + wc
        if total_metals > (1.0 - TACTICAL_CONSTRAINTS["cash"]["min"]):
            scale = (1.0 - TACTICAL_CONSTRAINTS["cash"]["min"]) / total_metals
            wg *= scale
            ws *= scale
            wc *= scale
            wk = TACTICAL_CONSTRAINTS["cash"]["min"]
        else:
            wk = 1.0 - total_metals
            wk = np.clip(wk, TACTICAL_CONSTRAINTS["cash"]["min"], TACTICAL_CONSTRAINTS["cash"]["max"])
            rem = 1.0 - (wg + ws + wc + wk)
            wg += rem * (BENCHMARK_WEIGHTS["gold"] / 0.92)
            ws += rem * (BENCHMARK_WEIGHTS["silver"] / 0.92)
            wc += rem * (BENCHMARK_WEIGHTS["copper"] / 0.92)

        w_gold.append(wg)
        w_silver.append(ws)
        w_copper.append(wc)
        w_cash.append(wk)

    out["weight_gold"] = w_gold
    out["weight_silver"] = w_silver
    out["weight_copper"] = w_copper
    out["weight_cash"] = w_cash

    return out


def run_portfolio_backtest(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    ts = df.copy()
    
    ts["bm_return"] = (
        BENCHMARK_WEIGHTS["gold"] * ts["gold_ret"]
        + BENCHMARK_WEIGHTS["silver"] * ts["silver_ret"]
        + BENCHMARK_WEIGHTS["copper"] * ts["copper_ret"]
        + BENCHMARK_WEIGHTS["cash"] * ts["cash_ret"]
    )

    w_g_lag = ts["weight_gold"].shift(1).fillna(BENCHMARK_WEIGHTS["gold"])
    w_s_lag = ts["weight_silver"].shift(1).fillna(BENCHMARK_WEIGHTS["silver"])
    w_c_lag = ts["weight_copper"].shift(1).fillna(BENCHMARK_WEIGHTS["copper"])
    w_k_lag = ts["weight_cash"].shift(1).fillna(BENCHMARK_WEIGHTS["cash"])

    ts["strat_gross_return"] = (
        w_g_lag * ts["gold_ret"]
        + w_s_lag * ts["silver_ret"]
        + w_c_lag * ts["copper_ret"]
        + w_k_lag * ts["cash_ret"]
    )

    dw_g = ts["weight_gold"].diff().abs().fillna(0)
    dw_s = ts["weight_silver"].diff().abs().fillna(0)
    dw_c = ts["weight_copper"].diff().abs().fillna(0)
    dw_k = ts["weight_cash"].diff().abs().fillna(0)
    
    ts["daily_turnover"] = (dw_g + dw_s + dw_c + dw_k) / 2.0
    ts["rebalance_cost"] = ts["daily_turnover"] * REBALANCE_COST_BPS

    ts["strat_net_return"] = ts["strat_gross_return"] - ts["rebalance_cost"]

    ts["nav_benchmark"] = (1 + ts["bm_return"]).cumprod() * 100.0
    ts["nav_strategy"] = (1 + ts["strat_net_return"]).cumprod() * 100.0

    ts["dd_benchmark"] = (ts["nav_benchmark"] - ts["nav_benchmark"].cummax()) / ts["nav_benchmark"].cummax() * 100.0
    ts["dd_strategy"] = (ts["nav_strategy"] - ts["nav_strategy"].cummax()) / ts["nav_strategy"].cummax() * 100.0

    ts["daily_alpha"] = ts["strat_net_return"] - ts["bm_return"]
    ts["cum_alpha"] = (ts["nav_strategy"] / ts["nav_benchmark"] - 1.0) * 100.0

    n_days = len(ts)
    years = n_days / 252.0

    cagr_strat = (ts["nav_strategy"].iloc[-1] / 100.0) ** (1.0 / years) - 1.0
    cagr_bm = (ts["nav_benchmark"].iloc[-1] / 100.0) ** (1.0 / years) - 1.0

    vol_strat = ts["strat_net_return"].std() * np.sqrt(252)
    vol_bm = ts["bm_return"].std() * np.sqrt(252)

    sharpe_strat = (cagr_strat - RISK_FREE_RATE_ANNUAL) / vol_strat if vol_strat > 0 else 0
    sharpe_bm = (cagr_bm - RISK_FREE_RATE_ANNUAL) / vol_bm if vol_bm > 0 else 0

    downside_strat = ts["strat_net_return"][ts["strat_net_return"] < 0].std() * np.sqrt(252)
    sortino_strat = (cagr_strat - RISK_FREE_RATE_ANNUAL) / downside_strat if downside_strat > 0 else 0

    max_dd_strat = ts["dd_strategy"].min()
    max_dd_bm = ts["dd_benchmark"].min()

    calmar_strat = cagr_strat / abs(max_dd_strat / 100.0) if max_dd_strat != 0 else 0

    cov_mat = np.cov(ts["strat_net_return"], ts["bm_return"])
    beta = cov_mat[0, 1] / cov_mat[1, 1] if cov_mat[1, 1] > 0 else 1.0
    alpha_jensen = (cagr_strat - RISK_FREE_RATE_ANNUAL) - beta * (cagr_bm - RISK_FREE_RATE_ANNUAL)

    te = ts["daily_alpha"].std() * np.sqrt(252)
    ir = (cagr_strat - cagr_bm) / te if te > 0 else 0

    avg_annual_turnover = ts["daily_turnover"].mean() * 252.0
    hit_rate = (ts["daily_alpha"] > 0).mean() * 100.0

    metrics = {
        "cagr_strategy_%": round(cagr_strat * 100, 2),
        "cagr_benchmark_%": round(cagr_bm * 100, 2),
        "alpha_annuel_%": round((cagr_strat - cagr_bm) * 100, 2),
        "alpha_jensen_%": round(alpha_jensen * 100, 2),
        "volatilite_strategy_%": round(vol_strat * 100, 2),
        "volatilite_benchmark_%": round(vol_bm * 100, 2),
        "sharpe_strategy": round(sharpe_strat, 3),
        "sharpe_benchmark": round(sharpe_bm, 3),
        "sortino_strategy": round(sortino_strat, 3),
        "max_drawdown_strategy_%": round(max_dd_strat, 2),
        "max_drawdown_benchmark_%": round(max_dd_bm, 2),
        "calmar_strategy": round(calmar_strat, 3),
        "beta": round(beta, 3),
        "tracking_error_%": round(te * 100, 2),
        "ratio_information": round(ir, 3),
        "turnover_annuel_%": round(avg_annual_turnover * 100, 1),
        "cout_turnover_annuel_bps": round(avg_annual_turnover * REBALANCE_COST_BPS * 10000, 1),
        "hit_rate_quotidien_%": round(hit_rate, 2),
        "nombre_jours": n_days,
    }

    return ts, metrics


def compute_risk_metrics(ts: pd.DataFrame) -> dict:
    ret = ts["strat_net_return"].dropna().values
    
    var_hist_95_1d = -float(np.percentile(ret, 5)) * 100.0
    var_hist_99_1d = -float(np.percentile(ret, 1)) * 100.0

    var_hist_95_10d = var_hist_95_1d * np.sqrt(10)
    var_hist_99_10d = var_hist_99_1d * np.sqrt(10)

    cvar_95_1d = -float(ret[ret <= np.percentile(ret, 5)].mean()) * 100.0
    cvar_99_1d = -float(ret[ret <= np.percentile(ret, 1)].mean()) * 100.0

    mu = float(ret.mean())
    sigma = float(ret.std(ddof=1))
    var_param_95_1d = -(mu + stats.norm.ppf(0.05) * sigma) * 100.0
    var_param_99_1d = -(mu + stats.norm.ppf(0.01) * sigma) * 100.0

    recent = ts[["gold_ret", "silver_ret", "copper_ret"]].iloc[-60:]
    corr_matrix = recent.corr().round(3).to_dict()

    return {
        "var_historique_95_1j_%": round(var_hist_95_1d, 2),
        "var_historique_99_1j_%": round(var_hist_99_1d, 2),
        "var_reglementaire_99_10j_%": round(var_hist_99_10d, 2),
        "expected_shortfall_cvar_95_1j_%": round(cvar_95_1d, 2),
        "expected_shortfall_cvar_99_1j_%": round(cvar_99_1d, 2),
        "var_parametrique_95_1j_%": round(var_param_95_1d, 2),
        "var_parametrique_99_1j_%": round(var_param_99_1d, 2),
        "correlation_recente_60j": corr_matrix,
    }


def run_stress_tests(current_weights: dict = None) -> list[dict]:
    if current_weights is None:
        current_weights = BENCHMARK_WEIGHTS

    scenarios = [
        {
            "scenario": "Choc Déflationniste / Flambée du Dollar (Type Mars 2020)",
            "description": "Appréciation brutale du Dollar (+6%), baisse générale des matières premières industrielles et liquidation d'urgence.",
            "chocs": {"gold": -0.04, "silver": -0.15, "copper": -0.12, "cash": 0.0},
            "probabilite": "Moyenne",
        },
        {
            "scenario": "Choc Stagflationniste & Taux Réels Négatifs (Type 2022)",
            "description": "Inflation persistante, choc énergétique, envolée de l'or et correction modérée du cuivre.",
            "chocs": {"gold": +0.08, "silver": +0.05, "copper": -0.06, "cash": +0.005},
            "probabilite": "Élevée",
        },
        {
            "scenario": "Récession Industrielle Mondiale (Crash Chinois)",
            "description": "Ralentissement majeur du secteur manufacturier et de l'immobilier chinois, effondrement du cuivre.",
            "chocs": {"gold": +0.03, "silver": -0.08, "copper": -0.18, "cash": 0.0},
            "probabilite": "Moyenne",
        },
        {
            "scenario": "Crise Géopolitique Majeure / Flight-to-Safety",
            "description": "Tensions géopolitiques sévères, ruée vers les actifs refuges (Or) et flambée de la volatilité.",
            "chocs": {"gold": +0.12, "silver": +0.08, "copper": -0.02, "cash": 0.0},
            "probabilite": "Moyenne-Haute",
        },
    ]

    results = []
    for sc in scenarios:
        impact_strat = sum(current_weights.get(m, 0.0) * sc["chocs"].get(m, 0.0) for m in ["gold", "silver", "copper", "cash"])
        impact_bm = sum(BENCHMARK_WEIGHTS.get(m, 0.0) * sc["chocs"].get(m, 0.0) for m in ["gold", "silver", "copper", "cash"])
        
        results.append({
            "scenario": sc["scenario"],
            "description": sc["description"],
            "probabilite": sc["probabilite"],
            "impact_strategie_%": round(impact_strat * 100, 2),
            "impact_benchmark_%": round(impact_bm * 100, 2),
            "protection_relative_%": round((impact_strat - impact_bm) * 100, 2),
        })

    return results


def simulate_moroccan_fx_context(ts: pd.DataFrame) -> dict:
    annual_hedge_cost = 0.0175
    daily_hedge_drag = (1 + annual_hedge_cost) ** (1 / 252) - 1
    daily_usd_mad_drift = (1 + 0.015) ** (1 / 252) - 1

    ts_fx = ts.copy()
    np.random.seed(42)
    ts_fx["usd_mad_sim_ret"] = np.random.normal(daily_usd_mad_drift, 0.003, len(ts_fx))
    
    ts_fx["strat_mad_unhedged"] = (1 + ts_fx["strat_net_return"]) * (1 + ts_fx["usd_mad_sim_ret"]) - 1
    ts_fx["strat_mad_hedged"] = ts_fx["strat_net_return"] - daily_hedge_drag

    cagr_unhedged = ((1 + ts_fx["strat_mad_unhedged"]).cumprod().iloc[-1]) ** (252 / len(ts_fx)) - 1
    cagr_hedged = ((1 + ts_fx["strat_mad_hedged"]).cumprod().iloc[-1]) ** (252 / len(ts_fx)) - 1

    return {
        "statut_reglementaire_ammc": "Conforme aux ratios prudentiels OPCVM Métaux & Matières Premières",
        "regime_change_bam": "Panier 60% EUR / 40% USD (Bande de fluctuation ±5%)",
        "cout_couverture_forward_annuel_%": round(annual_hedge_cost * 100, 2),
        "cagr_en_mad_non_couvert_%": round(cagr_unhedged * 100, 2),
        "cagr_en_mad_couvert_100_%": round(cagr_hedged * 100, 2),
        "recommandation_cdg": "Couverture dynamique partielle (50% passive) : réduit la vol FX sans pénaliser excessivement l'alpha",
    }


def run_full_portfolio_analysis():
    print("=" * 80)
    print("  GESTION QUANTITATIVE DE PORTEFEUILLE METAUX")
    print("=" * 80)

    df = load_and_enrich_data()
    enriched = compute_daily_scores_and_weights(df)
    ts, metrics = run_portfolio_backtest(enriched)
    ts.to_csv("portfolio_timeseries.csv")

    risk_metrics = compute_risk_metrics(ts)

    latest_weights = {
        "gold": ts["weight_gold"].iloc[-1],
        "silver": ts["weight_silver"].iloc[-1],
        "copper": ts["weight_copper"].iloc[-1],
        "cash": ts["weight_cash"].iloc[-1],
    }
    stress_results = run_stress_tests(latest_weights)
    fx_results = simulate_moroccan_fx_context(ts)

    summary_df = pd.DataFrame([metrics])
    summary_df.to_csv("portfolio_backtest_results.csv", index=False)

    return ts, metrics, risk_metrics, stress_results, fx_results


if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    run_full_portfolio_analysis()
