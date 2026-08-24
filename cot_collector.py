import pandas as pd
import requests

COT_DISAGG_URL = "https://publicreporting.cftc.gov/resource/72hh-3qpy.json"
COT_LEGACY_URL = "https://publicreporting.cftc.gov/resource/6dca-aqww.json"

MARKET_CODES = {
    "gold": "088691",
    "silver": "084691",
    "copper": "085692",
}


def fetch_cot(metal: str, limit: int = 260) -> pd.DataFrame:
    code = MARKET_CODES[metal]
    params = {
        "$where": f"cftc_contract_market_code='{code}'",
        "$order": "report_date_as_yyyy_mm_dd DESC",
        "$limit": str(limit),
    }
    
    df = pd.DataFrame()
    try:
        resp = requests.get(COT_DISAGG_URL, params=params, timeout=30)
        if resp.status_code == 200:
            df = pd.DataFrame(resp.json())
    except Exception:
        df = pd.DataFrame()

    if df.empty or "m_money_positions_long_all" not in df.columns:
        try:
            resp = requests.get(COT_LEGACY_URL, params=params, timeout=30)
            if resp.status_code == 200:
                df = pd.DataFrame(resp.json())
                if not df.empty:
                    df["m_money_positions_long_all"] = df.get("noncomm_positions_long_all", 0)
                    df["m_money_positions_short_all"] = df.get("noncomm_positions_short_all", 0)
        except Exception:
            return pd.DataFrame()

    if df.empty or "report_date_as_yyyy_mm_dd" not in df.columns:
        return pd.DataFrame()

    df["report_date_as_yyyy_mm_dd"] = pd.to_datetime(df["report_date_as_yyyy_mm_dd"])
    
    numeric_cols = [
        "m_money_positions_long_all", "m_money_positions_short_all",
        "noncomm_positions_long_all", "noncomm_positions_short_all",
    ]
    for column in numeric_cols:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)

    long_pos = df.get("m_money_positions_long_all", pd.Series(0, index=df.index))
    short_pos = df.get("m_money_positions_short_all", pd.Series(0, index=df.index))
    
    df["net_spec_position"] = long_pos - short_pos
    
    df = df.sort_values("report_date_as_yyyy_mm_dd")
    
    win = min(156, len(df))
    min_p = min(10, win)
    df["net_spec_percentile"] = (
        df["net_spec_position"]
        .rolling(window=win, min_periods=min_p)
        .rank(pct=True) * 100
    )

    return df


if __name__ == "__main__":
    for metal in MARKET_CODES:
        data = fetch_cot(metal, limit=8)
        cols = ["report_date_as_yyyy_mm_dd", "net_spec_position", "net_spec_percentile"]
        print(data[[column for column in cols if column in data.columns]].tail(8))
