import yfinance as yf
import pandas as pd
import requests
from io import StringIO
from datetime import datetime
from cot_collector import fetch_cot, MARKET_CODES

WEIGHTS = {"gold": 0.49, "silver": 0.16, "copper": 0.27}

TICKERS = {
    "gold_front": "GC=F",
    "silver_front": "SI=F",
    "copper_front": "HG=F",
    "dxy": "DX-Y.NYB",
    "gld_etf": "GLD",
    "slv_etf": "SLV",
    "cper_etf": "CPER",
    "gvz": "^GVZ",
}

FRED_SERIES = {
    "real_yield_10y": "DFII10",
    "breakeven_10y": "T10YIE",
    "treasury_10y": "DGS10",
    "industrial_production": "INDPRO",
}
FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"

LOOKBACK_PERIOD = "5y"


def fetch_prices(period: str = LOOKBACK_PERIOD) -> dict:
    data = {}
    for name, ticker in TICKERS.items():
        try:
            hist = yf.Ticker(ticker).history(period=period, interval="1d")
            if hist.empty:
                print(f"[ATTENTION] Aucune donnee pour {name} ({ticker})")
                continue
            hist = hist[["Close", "Volume"]].rename(
                columns={"Close": f"{name}_close", "Volume": f"{name}_volume"}
            )
            data[name] = hist
        except Exception as e:
            print(f"[ERREUR] {name} ({ticker}) : {e}")
    return data


def fetch_fred_series(series_id: str) -> pd.DataFrame:
    url = FRED_CSV_URL.format(series_id=series_id)
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    df = pd.read_csv(StringIO(resp.text))
    df.columns = ["date", series_id]
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")
    df[series_id] = pd.to_numeric(df[series_id], errors="coerce")
    return df


def fetch_macro_data() -> dict:
    data = {}
    for name, series_id in FRED_SERIES.items():
        try:
            data[name] = fetch_fred_series(series_id)
        except Exception as e:
            print(f"[ERREUR] FRED {name} ({series_id}) : {e}")
    return data


GLD_HOLDINGS_URL = "https://www.spdrgoldshares.com/assets/dynamic/GLD/GLD_US_archive_EN.csv"


def fetch_gld_official_holdings() -> pd.DataFrame:
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    resp = requests.get(GLD_HOLDINGS_URL, headers=headers, timeout=30)
    resp.raise_for_status()

    raw_text = resp.text
    if not raw_text or "Date" not in raw_text:
        return pd.DataFrame()

    lines = raw_text.splitlines()
    header_idx = next((i for i, l in enumerate(lines) if l.strip().startswith("Date")), None)
    if header_idx is None:
        return pd.DataFrame()

    csv_body = "\n".join(lines[header_idx:])
    df = pd.read_csv(
        StringIO(csv_body), skipinitialspace=True,
        engine="python", on_bad_lines="skip",
    )
    if df.empty:
        return pd.DataFrame()

    df.columns = [c.strip() for c in df.columns]
    if "Date" not in df.columns:
        return pd.DataFrame()

    tonnes_col = next((c for c in df.columns if "Tonnes" in c), None)
    if tonnes_col is None:
        return pd.DataFrame()

    df["date"] = pd.to_datetime(df["Date"], format="%d-%b-%Y", errors="coerce")
    df = df.dropna(subset=["date"]).set_index("date")
    df = df.rename(columns={tonnes_col: "gld_tonnes_held"})
    df["gld_tonnes_held"] = pd.to_numeric(df["gld_tonnes_held"], errors="coerce")

    return df[["gld_tonnes_held"]]


def _strip_timezone(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.index, pd.DatetimeIndex) and df.index.tz is not None:
        df = df.copy()
        df.index = df.index.tz_localize(None)
    return df


_FRED_RENAME = {
    "DFII10": "real_yield_10y",
    "T10YIE": "breakeven_10y",
    "DGS10":  "treasury_10y",
    "INDPRO": "industrial_production",
}


def merge_data(data: dict) -> pd.DataFrame:
    frames = [_strip_timezone(df) for df in data.values()]
    merged = pd.concat(frames, axis=1, join="outer", sort=False)
    merged = merged.sort_index().ffill()

    merged = merged.rename(columns={k: v for k, v in _FRED_RENAME.items() if k in merged.columns})

    price_cols = [c for c in ["gold_front_close", "silver_front_close", "copper_front_close"]
                  if c in merged.columns]
    if price_cols:
        first_valid_dates = [merged[c].first_valid_index() for c in price_cols]
        first_valid_dates = [d for d in first_valid_dates if d is not None]
        if first_valid_dates:
            start_date = max(first_valid_dates, key=lambda d: d)
            merged = merged[merged.index >= start_date]

    return merged


def _add_price_variations(out: pd.DataFrame, cols: list) -> pd.DataFrame:
    for col in cols:
        if col in out.columns:
            out[f"{col}_var_1j"] = out[col].pct_change(1) * 100
            out[f"{col}_var_5j"] = out[col].pct_change(5) * 100
    return out


def _add_realized_vol(out: pd.DataFrame, price_col: str, out_name: str) -> pd.DataFrame:
    if price_col in out.columns:
        daily_ret = out[price_col].pct_change()
        out[out_name] = daily_ret.rolling(20).std() * (252 ** 0.5) * 100
    return out


def _add_zscore(out: pd.DataFrame, col: str, window: int = 60) -> pd.DataFrame:
    if col in out.columns:
        roll_mean = out[col].rolling(window).mean()
        roll_std = out[col].rolling(window).std()
        out[f"{col}_zscore"] = (out[col] - roll_mean) / roll_std
    return out


def compute_gold_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out = _add_price_variations(out, ["gold_front_close", "dxy_close"])
    out = _add_realized_vol(out, "gold_front_close", "gold_realized_vol_20j")
    out = _add_zscore(out, "real_yield_10y")
    out = _add_zscore(out, "breakeven_10y")
    out = _add_zscore(out, "dxy_close")

    if "gld_tonnes_held" in out.columns:
        out["gld_flow_tonnes_1j"] = out["gld_tonnes_held"].diff()
        out["gld_flow_tonnes_5j"] = out["gld_tonnes_held"].diff(5)
        out = _add_zscore(out, "gld_flow_tonnes_5j")
    elif "gld_etf_volume" in out.columns:
        ma20 = out["gld_etf_volume"].rolling(20).mean()
        out["gld_etf_flow_signal"] = (out["gld_etf_volume"].rolling(5).mean() / ma20) - 1
        out = _add_zscore(out, "gld_etf_flow_signal")

    if "gvz_close" in out.columns:
        out = _add_zscore(out, "gvz_close")

    return out


def compute_silver_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out = _add_price_variations(out, ["silver_front_close"])
    out = _add_realized_vol(out, "silver_front_close", "silver_realized_vol_20j")

    if "gold_front_close" in out.columns and "silver_front_close" in out.columns:
        out["gold_silver_ratio"] = out["gold_front_close"] / out["silver_front_close"]
        out = _add_zscore(out, "gold_silver_ratio")

    out = _add_zscore(out, "industrial_production")

    if "slv_etf_volume" in out.columns:
        ma20 = out["slv_etf_volume"].rolling(20).mean()
        out["slv_etf_flow_signal"] = (out["slv_etf_volume"].rolling(5).mean() / ma20) - 1

    return out


def compute_copper_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out = _add_price_variations(out, ["copper_front_close"])
    out = _add_realized_vol(out, "copper_front_close", "copper_realized_vol_20j")

    if "copper_front_close" in out.columns and "gold_front_close" in out.columns:
        out["copper_gold_ratio"] = (out["copper_front_close"] / out["gold_front_close"]) * 1000
        out = _add_zscore(out, "copper_gold_ratio")

    out = _add_zscore(out, "treasury_10y")
    out = _add_zscore(out, "industrial_production")

    if "cper_etf_volume" in out.columns:
        ma20 = out["cper_etf_volume"].rolling(20).mean()
        out["cper_etf_flow_signal"] = (out["cper_etf_volume"].rolling(5).mean() / ma20) - 1

    return out


def compute_composite_score(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["panier_perf_1j"] = (
        out.get("gold_front_close_var_1j", 0) * WEIGHTS["gold"]
        + out.get("silver_front_close_var_1j", 0) * WEIGHTS["silver"]
        + out.get("copper_front_close_var_1j", 0) * WEIGHTS["copper"]
    )
    return out


def fetch_cot_data() -> dict:
    cot_frames = {}
    for metal in MARKET_CODES:
        try:
            df = fetch_cot(metal, limit=260)
            if df.empty:
                continue
            df = df.set_index("report_date_as_yyyy_mm_dd")
            cols_keep = ["net_spec_position", "net_spec_percentile"]
            cols_keep = [c for c in cols_keep if c in df.columns]
            if not cols_keep:
                continue
            df = df[cols_keep].rename(columns={
                "net_spec_position": f"cot_{metal}_net_spec",
                "net_spec_percentile": f"cot_{metal}_percentile",
            })
            cot_frames[f"cot_{metal}"] = df
        except Exception as e:
            print(f"[ATTENTION] COT {metal} indisponible : {e}")
    return cot_frames


def compute_cot_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for metal in MARKET_CODES:
        col = f"cot_{metal}_net_spec"
        if col in out.columns:
            out = _add_zscore(out, col)
    return out


def run(save_csv: bool = True) -> pd.DataFrame:
    print(f"[{datetime.now():%Y-%m-%d %H:%M}] Recuperation des donnees marche (Yahoo Finance)...")
    raw = fetch_prices()
    if not raw:
        raise RuntimeError("Aucune donnee recuperee. Verifier la connexion internet.")

    print(f"[{datetime.now():%Y-%m-%d %H:%M}] Recuperation des donnees macro (FRED)...")
    raw.update(fetch_macro_data())

    print(f"[{datetime.now():%Y-%m-%d %H:%M}] Recuperation des avoirs officiels GLD...")
    try:
        holdings = fetch_gld_official_holdings()
        if not holdings.empty:
            raw["gld_holdings"] = holdings
        else:
            print("[ATTENTION] Avoirs GLD officiels indisponibles, repli sur proxy volume.")
    except Exception as e:
        print(f"[ATTENTION] Avoirs GLD officiels indisponibles, repli sur proxy volume : {e}")

    print(f"[{datetime.now():%Y-%m-%d %H:%M}] Recuperation des donnees COT (CFTC)...")
    try:
        cot_data = fetch_cot_data()
        raw.update(cot_data)
    except Exception as e:
        print(f"[ATTENTION] Donnees COT indisponibles : {e}")

    merged = merge_data(raw)

    with_gold = compute_gold_indicators(merged)
    with_silver = compute_silver_indicators(with_gold)
    with_copper = compute_copper_indicators(with_silver)
    with_composite = compute_composite_score(with_copper)
    final = compute_cot_indicators(with_composite)

    if save_csv:
        out_path = "metaux_daily_data.csv"
        final.to_csv(out_path)
        print(f"Donnees sauvegardees -> {out_path}")

    return final


def print_summary(df: pd.DataFrame) -> None:
    print("\n=== OR (49%) ===")
    cols = ["gold_front_close", "gold_front_close_var_1j", "real_yield_10y",
            "breakeven_10y", "dxy_close", "gvz_close", "gold_realized_vol_20j",
            "gld_tonnes_held", "gld_flow_tonnes_5j"]
    print(df[[c for c in cols if c in df.columns]].tail(3))

    print("\n=== ARGENT (16%) ===")
    cols = ["silver_front_close", "silver_front_close_var_1j", "gold_silver_ratio",
            "gold_silver_ratio_zscore", "industrial_production", "silver_realized_vol_20j"]
    print(df[[c for c in cols if c in df.columns]].tail(3))

    print("\n=== CUIVRE (27%) ===")
    cols = ["copper_front_close", "copper_front_close_var_1j", "copper_gold_ratio",
            "copper_gold_ratio_zscore", "treasury_10y", "copper_realized_vol_20j"]
    print(df[[c for c in cols if c in df.columns]].tail(3))

    print("\n=== PANIER CDG (49/16/27) ===")
    print(df[["panier_perf_1j"]].tail(5))


if __name__ == "__main__":
    df = run()
    print_summary(df)
