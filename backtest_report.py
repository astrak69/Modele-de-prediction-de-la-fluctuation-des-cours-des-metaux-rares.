from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from pandas.api.types import is_scalar
from typing import Any, cast

RESULTS_FILE = "backtest_results.csv"
OUTPUT_FILE  = "backtest_report.html"
TRANSACTION_COST_PCT = 0.05
P_THRESHOLD  = 0.05


def _fmt(val, decimals: int = 2, suffix: str = "") -> str:
    if val is None:
        return "<span class='na'>—</span>"
    if isinstance(val, str):
        if val.strip() == "" or val.lower() in {"nan", "none", "null"}:
            return "<span class='na'>—</span>"
        return val
    if isinstance(val, (float, np.floating)) and math.isnan(float(val)):
        return "<span class='na'>—</span>"
    if isinstance(val, (int, float, np.integer, np.floating)):
        return f"{val:.{decimals}f}{suffix}"
    return str(val)


def _verdict_class(verdict: str) -> str:
    if "priorité haute" in verdict:
        return "verdict-green"
    if "surveiller" in verdict:
        return "verdict-amber"
    if "manquantes" in verdict or "erreur" in verdict.lower():
        return "verdict-red"
    return "verdict-red"


def _p_class(p) -> str:
    if p is None or (isinstance(p, float) and math.isnan(p)):
        return ""
    return "p-sig" if p < P_THRESHOLD else "p-insig"


def _metal_label(col: str) -> str:
    return {"gold_front_close": "Or", "silver_front_close": "Argent",
            "copper_front_close": "Cuivre"}.get(col, col)


def _horizon_label(h: int) -> str:
    return f"J+{h}"


                                                                                
     
                                                                                

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg:         #0d1117;
  --surface:    #161b22;
  --surface2:   #21262d;
  --border:     #30363d;
  --text:       #e6edf3;
  --muted:      #8b949e;
  --green:      #3fb950;
  --green-dim:  #1a3d24;
  --amber:      #d29922;
  --amber-dim:  #3d2e00;
  --red:        #f85149;
  --red-dim:    #3d1a19;
  --blue:       #58a6ff;
  --gold:       #e3b341;
  --gold-dim:   #3d2e00;
  --radius:     10px;
  --shadow:     0 4px 24px rgba(0,0,0,.45);
}

body {
  font-family: 'Inter', sans-serif;
  background: var(--bg);
  color: var(--text);
  font-size: 14px;
  line-height: 1.6;
}

.page { max-width: 1400px; margin: 0 auto; padding: 0 24px 60px; }

.cover {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 72px 24px 60px;
  border-bottom: 1px solid var(--border);
  background: linear-gradient(160deg, #0d1117 0%, #151b27 100%);
  position: relative;
  overflow: hidden;
}
.cover::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse 700px 400px at 20% 80%, rgba(88,166,255,.06) 0%, transparent 70%),
    radial-gradient(ellipse 500px 300px at 80% 20%, rgba(227,179,65,.07) 0%, transparent 70%);
  pointer-events: none;
}
.cover-logo {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 3px;
  text-transform: uppercase;
  color: var(--gold);
  margin-bottom: 20px;
}
.cover h1 {
  font-size: clamp(26px, 4vw, 42px);
  font-weight: 700;
  color: var(--text);
  line-height: 1.2;
  margin-bottom: 14px;
}
.cover-sub {
  font-size: 15px;
  color: var(--muted);
  max-width: 620px;
  margin-bottom: 32px;
}
.cover-meta {
  display: flex;
  gap: 32px;
  flex-wrap: wrap;
  justify-content: center;
  font-size: 12px;
  color: var(--muted);
}
.cover-meta span strong { color: var(--text); }

.section {
  margin-top: 52px;
}
.section-title {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--gold);
  margin-bottom: 4px;
}
.section h2 {
  font-size: 22px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 20px;
  border-bottom: 1px solid var(--border);
  padding-bottom: 12px;
}

.kpi-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 14px;
  margin-bottom: 32px;
}
.kpi-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 18px 20px;
  position: relative;
  overflow: hidden;
}
.kpi-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 3px;
}
.kpi-card.green::before { background: var(--green); }
.kpi-card.amber::before { background: var(--amber); }
.kpi-card.blue::before  { background: var(--blue);  }
.kpi-card.gold::before  { background: var(--gold);  }
.kpi-card.red::before   { background: var(--red);   }
.kpi-label {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: .5px;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 6px;
}
.kpi-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--text);
  line-height: 1;
}
.kpi-sub {
  font-size: 11px;
  color: var(--muted);
  margin-top: 4px;
}

.table-wrap { overflow-x: auto; border-radius: var(--radius); border: 1px solid var(--border); }
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12.5px;
}
thead th {
  background: var(--surface2);
  color: var(--muted);
  font-weight: 600;
  font-size: 11px;
  letter-spacing: .5px;
  text-transform: uppercase;
  padding: 11px 14px;
  text-align: left;
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
  position: sticky;
  top: 0;
}
tbody tr {
  border-bottom: 1px solid var(--border);
  transition: background .15s;
}
tbody tr:last-child { border-bottom: none; }
tbody tr:hover { background: var(--surface2); }
tbody td { padding: 10px 14px; vertical-align: middle; white-space: nowrap; }
.num { text-align: right; font-variant-numeric: tabular-nums; }

.badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
}
.verdict-green { background: var(--green-dim); color: var(--green); }
.verdict-amber { background: var(--amber-dim); color: var(--amber); }
.verdict-red   { background: var(--red-dim);   color: var(--red);   }

.p-sig   { color: var(--green); font-weight: 600; }
.p-insig { color: var(--red); }
.na      { color: var(--border); }

.heatmap-grid {
  overflow-x: auto;
  border-radius: var(--radius);
  border: 1px solid var(--border);
}
.heatmap-grid table { font-size: 12px; }
.heatmap-grid thead th { background: var(--surface2); }
.hm-cell {
  text-align: center;
  padding: 10px 18px;
  font-weight: 600;
  border-radius: 4px;
  transition: filter .2s;
}
.hm-cell:hover { filter: brightness(1.25); cursor: default; }

.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(580px, 1fr));
  gap: 20px;
}
.signal-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 24px;
  box-shadow: var(--shadow);
  position: relative;
  overflow: hidden;
}
.signal-card::before {
  content: '';
  position: absolute;
  inset: 0 0 auto 0;
  height: 3px;
}
.card-green::before { background: linear-gradient(90deg, var(--green), #2ea043); }
.card-amber::before { background: linear-gradient(90deg, var(--amber), #b08800); }
.card-red::before   { background: linear-gradient(90deg, var(--red),   #c93b38); }

.card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}
.card-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
  line-height: 1.4;
}
.card-sub {
  font-size: 11px;
  color: var(--muted);
  margin-top: 3px;
}
.card-stat-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  margin-bottom: 16px;
}
.card-stat {
  background: var(--surface2);
  border-radius: 8px;
  padding: 10px 12px;
}
.card-stat-label { font-size: 10px; color: var(--muted); font-weight: 600; text-transform: uppercase; letter-spacing: .5px; }
.card-stat-value { font-size: 18px; font-weight: 700; color: var(--text); margin-top: 2px; }
.card-stat-value.pos { color: var(--green); }
.card-stat-value.neg { color: var(--red);   }
.chart-wrap { height: 140px; position: relative; }

.method-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 14px;
}
.method-item {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 18px 20px;
}
.method-item h4 {
  font-size: 13px;
  font-weight: 600;
  color: var(--gold);
  margin-bottom: 6px;
}
.method-item p {
  font-size: 12px;
  color: var(--muted);
  line-height: 1.6;
}

.footer {
  margin-top: 60px;
  padding-top: 24px;
  border-top: 1px solid var(--border);
  font-size: 11px;
  color: var(--muted);
  text-align: center;
  line-height: 1.8;
}
"""


                                                                                
                       
                                                                                

def _hm_style(val) -> str:
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return "background:#21262d; color:#8b949e;"
    v = float(val)
    if v > 1.5:
        return "background:#1a3d24; color:#3fb950;"
    if v > 0.5:
        return "background:#1e3a20; color:#56d364;"
    if v > 0:
        return "background:#1b2e1b; color:#7ee787;"
    if v > -0.5:
        return "background:#3d1a19; color:#f85149;"
    return "background:#4d1313; color:#ff7b72;"


                                                                                
               
                                                                                

def build_kpi_strip(df: pd.DataFrame) -> str:
    total     = len(df)
    errors    = int(df["erreur"].notna().sum()) if "erreur" in df.columns else 0
    working   = total - errors
    n_sig     = int(df[df["verdict"].str.contains("priorité haute", na=False)]["signal"].nunique())
    n_watch   = int(df[df["verdict"].str.contains("surveiller",    na=False)]["signal"].nunique())
    n_reject  = int(df[df["verdict"].str.contains("Non sig|Non rob|insuff", na=False, regex=True)]["signal"].nunique())

    sig_df = df[df["verdict"].str.contains("priorité haute", na=False)]
    best_ir = sig_df["ratio_information"].max() if "ratio_information" in sig_df.columns and not sig_df.empty else float("nan")

    cards = [
        ("Signaux testés",    f"{working}",       "sur {total} configurés".format(total=total), "blue"),
        ("✅ Priorité haute", f"{n_sig}",          "signaux institutionnels",                    "green"),
        ("🔶 À surveiller",  f"{n_watch}",         "signaux robustes / alpha modéré",            "amber"),
        ("❌ Écartés",        f"{n_reject}",        "non significatifs ou non robustes",          "red"),
        ("Meilleur IR",       _fmt(best_ir, 2),    "ratio d'information (signal prioritaire)",   "gold"),
    ]
    parts = []
    for label, value, sub, cls in cards:
        parts.append(f"""
        <div class="kpi-card {cls}">
          <div class="kpi-label">{label}</div>
          <div class="kpi-value">{value}</div>
          <div class="kpi-sub">{sub}</div>
        </div>""")
    return f'<div class="kpi-strip">{"".join(parts)}</div>'


def build_daily_snapshot(data_file: str = "metaux_daily_data.csv") -> str:
    try:
        df = pd.read_csv(data_file, index_col=0, parse_dates=True).sort_index()
    except FileNotFoundError:
        return "<p style='color:var(--muted)'>Snapshot quotidien indisponible : fichier de données introuvable.</p>"

    if df.empty:
        return "<p style='color:var(--muted)'>Snapshot quotidien indisponible : aucune donnée chargée.</p>"

    latest = df.iloc[-1]
    latest_idx = df.index[-1] if len(df.index) > 0 else None
    latest_date = latest_idx.strftime("%d %B %Y") if (latest_idx is not None and hasattr(latest_idx, "strftime")) else "n/a"

    rows = [
        ("Date du snapshot", latest_date),
        ("Or (front)", latest.get("gold_front_close")),
        ("Argent (front)", latest.get("silver_front_close")),
        ("Cuivre (front)", latest.get("copper_front_close")),
        ("DXY", latest.get("dxy_close")),
        ("GVZ", latest.get("gvz_close")),
        ("Real Yield 10Y z-score", latest.get("real_yield_10y_zscore")),
        ("Gold/Silver ratio z-score", latest.get("gold_silver_ratio_zscore")),
        ("Copper/Gold ratio z-score", latest.get("copper_gold_ratio_zscore")),
    ]

    cells = "".join(
        f"<tr><td>{label}</td><td class='num'>{_fmt(value, 3)}</td></tr>"
        for label, value in rows
    )

    return f"""
    <p style="color:var(--muted);font-size:12px;margin-bottom:12px">
      Cette section reflète la dernière journée disponible du fichier de données quotidien (données fraîches).
      Les métriques de backtest ci-dessous sont calculées sur l'historique antérieur aux 90 derniers jours.
    </p>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Indicateur</th><th class="num">Valeur</th></tr></thead>
        <tbody>{cells}</tbody>
      </table>
    </div>"""


def build_summary_table(df: pd.DataFrame) -> str:
                                                                                         
    summary_rows = []
    for sig_name, grp in df.groupby("signal", sort=False):
                                            
        def _verdict_rank(v: str) -> int:
            if "priorité haute" in v: return 0
            if "surveiller"     in v: return 1
            if "Données"        in v: return 9
            return 2
        grp_sorted = grp.assign(_rank=grp["verdict"].map(_verdict_rank)).sort_values(["_rank", "horizon_j"])
        best = grp_sorted.iloc[0]
        summary_rows.append(best)

    rows_html = []
    for r in summary_rows:
        vcls = _verdict_class(str(r.get("verdict", "")))
        pcls = _p_class(r.get("p_value"))
        metal = _metal_label(str(r.get("metal", "")))
        dir_icon = "🔼" if str(r.get("direction","")) == "Long" else "🔽"
        rows_html.append(f"""
        <tr>
          <td>{r['signal']}</td>
          <td>{metal}</td>
          <td>{dir_icon} {r.get('direction','—')}</td>
          <td class="num">{_fmt(r.get('occurrences'), 0)}</td>
          <td class="num">{_fmt(r.get('rendement_brut_%'), 3, ' %')}</td>
          <td class="num">{_fmt(r.get('rendement_net_%'),  3, ' %')}</td>
          <td class="num">{_fmt(r.get('rendement_baseline_%'), 3, ' %')}</td>
          <td class="num {pcls}">{_fmt(r.get('p_value'), 4)}</td>
          <td class="num">{_fmt(r.get('ratio_information'), 3)}</td>
          <td class="num">{_fmt(r.get('taux_succes_%'), 1, ' %')}</td>
          <td class="num">{_fmt(r.get('max_drawdown_%'), 2, ' %')}</td>
          <td><span class="badge {vcls}">{r.get('verdict','—')}</span></td>
        </tr>""")

    return f"""
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Signal</th><th>Métal</th><th>Sens</th>
            <th class="num">Occ.</th>
            <th class="num">Rdt brut</th>
            <th class="num">Rdt net</th>
            <th class="num">Baseline</th>
            <th class="num">p-value</th>
            <th class="num">Ratio Info</th>
            <th class="num">Taux succès</th>
            <th class="num">Max DD</th>
            <th>Verdict</th>
          </tr>
        </thead>
        <tbody>{"".join(rows_html)}</tbody>
      </table>
    </div>"""


def build_heatmap(df: pd.DataFrame) -> str:
    horizons = sorted(df["horizon_j"].dropna().unique().astype(int).tolist())
    signals  = df["signal"].unique().tolist()

    header = "<tr><th>Signal</th>" + "".join(f"<th>{_horizon_label(h)}</th>" for h in horizons) + "</tr>"
    rows   = []
    for sig in signals:
        row = f"<tr><td style='padding:10px 14px;white-space:nowrap;font-size:12px'>{sig}</td>"
        for h in horizons:
            cell = df[(df["signal"] == sig) & (df["horizon_j"] == h)]
            if cell.empty:
                row += "<td class='hm-cell' style='background:#21262d;color:#8b949e'>—</td>"
            else:
                val = cell.iloc[0].get("rendement_net_%")
                txt = _fmt(val, 2, "%") if val is not None and not (isinstance(val, float) and math.isnan(val)) else "—"
                row += f"<td class='hm-cell' style='{_hm_style(val)}'>{txt}</td>"
        row += "</tr>"
        rows.append(row)

    return f"""
    <div class="heatmap-grid">
      <table><thead>{header}</thead><tbody>{"".join(rows)}</tbody></table>
    </div>"""


def build_signal_cards(df: pd.DataFrame) -> str:
    horizons = sorted(df["horizon_j"].dropna().unique().astype(int).tolist())
    cards = []
    chart_idx = 0

    for sig_name, grp in df.groupby("signal", sort=False):
        grp = grp.sort_values("horizon_j")
        best_row = grp.iloc[0]                                                  

                                      
        def _vrank(v): return 0 if "priorité" in str(v) else (1 if "surveiller" in str(v) else 2)
        best_verdict_row = grp.loc[grp["verdict"].map(_vrank).idxmin()]
        verdict = str(best_verdict_row.get("verdict", ""))
        vcls = _verdict_class(verdict)
        card_cls = vcls.replace("verdict-", "card-")

        metal = _metal_label(str(best_row.get("metal", "")))
        direction = str(best_row.get("direction", ""))
        col_sig = str(best_row.get("colonne_signal", ""))

                                                                                  
        valid = grp.dropna(subset=["rendement_net_%"])
        if not valid.empty:
          if "ratio_information" in valid.columns and valid["ratio_information"].notna().any():
            best_net_row = valid.loc[valid["ratio_information"].idxmax()]
          else:
            best_net_row = valid.loc[valid["rendement_net_%"].idxmax()]
        else:
            best_net_row = grp.iloc[0]

        n_occ  = best_net_row.get("occurrences", None)
        rdt    = best_net_row.get("rendement_net_%", None)
        pval   = best_net_row.get("p_value", None)
        ir_val = best_net_row.get("ratio_information", None)
        hr_val = best_net_row.get("taux_succes_%", None)
        p_cls  = _p_class(pval)
        rdt_val = None
        try:
          rdt_val = float(cast(Any, rdt))
        except Exception:
          rdt_val = None
        rdt_cls = "pos" if (rdt_val is not None and rdt_val > 0) else "neg"

                    
        chart_data_brut = []
        chart_data_net  = []
        chart_data_base = []
        chart_labels    = []
        for _, row in grp.iterrows():
            h = row.get("horizon_j")
            if h is None: continue
            chart_labels.append(_horizon_label(int(h)))
            brut_val = row.get("rendement_brut_%")
            net_val  = row.get("rendement_net_%")
            base_val = row.get("rendement_baseline_%")
            chart_data_brut.append(None if (brut_val is None or pd.isna(brut_val)) else round(float(brut_val), 4))
            chart_data_net.append(None  if (net_val is None  or pd.isna(net_val))  else round(float(net_val),  4))
            chart_data_base.append(None if (base_val is None or pd.isna(base_val)) else round(float(base_val), 4))

        cid = f"chart_{chart_idx}"
        chart_idx += 1

        chart_js = f"""
        new Chart(document.getElementById('{cid}'), {{
          type: 'line',
          data: {{
            labels: {json.dumps(chart_labels)},
            datasets: [
              {{
                label: 'Rdt brut',
                data: {json.dumps(chart_data_brut)},
                borderColor: '#58a6ff', backgroundColor: 'rgba(88,166,255,.12)',
                borderWidth: 2, pointRadius: 4, tension: 0.35, fill: false
              }},
              {{
                label: 'Rdt net',
                data: {json.dumps(chart_data_net)},
                borderColor: '#3fb950', backgroundColor: 'rgba(63,185,80,.12)',
                borderWidth: 2, pointRadius: 4, tension: 0.35, fill: false
              }},
              {{
                label: 'Baseline',
                data: {json.dumps(chart_data_base)},
                borderColor: '#8b949e', borderDash: [4,4],
                borderWidth: 1.5, pointRadius: 2, tension: 0.35, fill: false
              }}
            ]
          }},
          options: {{
            responsive: true, maintainAspectRatio: false,
            plugins: {{
              legend: {{ labels: {{ color: '#8b949e', font: {{ size: 10 }} }} }},
              tooltip: {{ callbacks: {{ label: ctx => ctx.dataset.label + ': ' + (ctx.parsed.y != null ? ctx.parsed.y.toFixed(3) + ' %' : '—') }} }}
            }},
            scales: {{
              x: {{ grid: {{ color: '#21262d' }}, ticks: {{ color: '#8b949e', font: {{ size: 10 }} }} }},
              y: {{
                grid: {{ color: '#21262d' }},
                ticks: {{ color: '#8b949e', font: {{ size: 10 }},
                         callback: v => v.toFixed(2) + '%' }},
                title: {{ display: true, text: 'Rendement (%)', color: '#8b949e', font: {{ size: 10 }} }}
              }}
            }}
          }}
        }});"""

                                       
        p1 = _fmt(best_net_row.get("rendement_p1_%"), 3, "%")
        p2 = _fmt(best_net_row.get("rendement_p2_%"), 3, "%")
        p3 = _fmt(best_net_row.get("rendement_p3_%"), 3, "%")
        ic_low  = _fmt(best_net_row.get("ic_95_bas_%"),  3, "%")
        ic_high = _fmt(best_net_row.get("ic_95_haut_%"), 3, "%")
        robust_flag = best_net_row.get("robuste_3_periodes")
        robust = False
        try:
          robust = bool(cast(Any, robust_flag))
        except Exception:
          robust = False
        rob = "✅ Oui" if robust else "❌ Non"

        card_html = f"""
        <div class="signal-card {card_cls}">
          <div class="card-header">
            <div>
              <div class="card-title">{sig_name}</div>
              <div class="card-sub">
                {metal} · {direction} · Signal&nbsp;: <code style="font-size:10px;color:var(--muted)">{col_sig}</code>
              </div>
            </div>
            <span class="badge {vcls}" style="flex-shrink:0">{verdict}</span>
          </div>
          <div class="card-stat-row">
            <div class="card-stat">
              <div class="card-stat-label">Rdt net (meilleur horizon)</div>
              <div class="card-stat-value {rdt_cls}">{_fmt(rdt, 3, "%")}</div>
            </div>
            <div class="card-stat">
              <div class="card-stat-label">p-value</div>
              <div class="card-stat-value {p_cls}">{_fmt(pval, 4)}</div>
            </div>
            <div class="card-stat">
              <div class="card-stat-label">Ratio Info.</div>
              <div class="card-stat-value">{_fmt(ir_val, 3)}</div>
            </div>
            <div class="card-stat">
              <div class="card-stat-label">Taux succès</div>
              <div class="card-stat-value">{_fmt(hr_val, 1, "%")}</div>
            </div>
          </div>
          <div class="chart-wrap">
            <canvas id="{cid}"></canvas>
          </div>
          <div style="display:flex;gap:24px;margin-top:14px;flex-wrap:wrap;font-size:11px;color:var(--muted)">
            <span>Occurrences&nbsp;: <strong style="color:var(--text)">{_fmt(n_occ, 0)}</strong></span>
            <span>IC&nbsp;95&nbsp;%&nbsp;: <strong style="color:var(--text)">[{ic_low} ; {ic_high}]</strong></span>
            <span>Robuste 3 périodes&nbsp;: <strong style="color:var(--text)">{rob}</strong></span>
            <span>Rdt P1/P2/P3&nbsp;: <strong style="color:var(--text)">{p1} / {p2} / {p3}</strong></span>
          </div>
        </div>
        <script>{chart_js}</script>"""
        cards.append(card_html)

    return f'<div class="cards-grid">{"".join(cards)}</div>'


def build_methodology() -> str:
    items = [
        ("Données", f"Yahoo Finance (futures frontaux GC=F, SI=F, HG=F) + ETFs (GLD, SLV, CPER) + FRED (DFII10, DGS10, T10YIE, INDPRO). Historique 5 ans."),
        ("Signaux", "Z-scores glissants 60 jours sur ratios, flux ETF et volatilité implicite. Seuils d'activation : |z| > 1,5 ou 2,0 selon le signal."),
        ("Horizons testés", "J+1, J+5, J+10, J+20 et J+60 (jours ouvrés). Rendements en prix de clôture futures frontaux."),
        ("Baseline", "Rendement moyen conditionnel sur les jours HORS signal (benchmark non contaminé)."),
        ("Robustesse", "Découpage de l'historique en 3 sous-périodes égales. Signal validé uniquement si le sens est identique dans les 3 sous-périodes avec ≥ 10 occurrences chacune."),
        ("Significativité", f"Test t de Student bilatéral de Welch (p < {P_THRESHOLD}). Intervalle de confiance bootstrap 95 % (1 000 resamples, seed 42)."),
        ("Coûts", f"Déduction forfaitaire de {TRANSACTION_COST_PCT:.2f} % aller-retour (spread bid-ask + frais de courtage, hypothèse prime brokerage institutionnel)."),
        ("Métriques", "Ratio d'information = (μ_signal − μ_baseline) / σ_signal. Taux de succès = % d'occurrences avec rendement > 0. Max drawdown intra-signal cumulé."),
        ("Verdict", "✅ Priorité haute : robuste + p < 5 % + IC entièrement positif + alpha > 1,5× baseline. 🔶 À surveiller : robuste + significatif mais alpha modéré."),
        ("Avertissement", "Ce rapport est produit à des fins d'analyse interne uniquement. Les performances passées ne préjugent pas des performances futures."),
    ]
    blocks = "".join(f"""
    <div class="method-item">
      <h4>{title}</h4>
      <p>{desc}</p>
    </div>""" for title, desc in items)
    return f'<div class="method-grid">{blocks}</div>'


def build_report(results_file: str = RESULTS_FILE, output: str = OUTPUT_FILE, data_file: str = "metaux_daily_data.csv") -> None:
    df = pd.read_csv(results_file)
    df = df.where(pd.notna(df), None)

    now = datetime.now()
    date_str  = now.strftime("%d %B %Y")
    time_str  = now.strftime("%H:%M")
    n_signals = df["signal"].nunique()
    n_horizons = int(df["horizon_j"].nunique())
    date_min = "(données 5 ans)"

    chart_script_tag = '<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>'

    daily_snapshot = build_daily_snapshot(data_file)
    kpi_strip      = build_kpi_strip(df)
    summary_table  = build_summary_table(df)
    heatmap        = build_heatmap(df)
    signal_cards   = build_signal_cards(df)
    methodology    = build_methodology()

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Rapport Backtest Quantitatif — CDG Capital Gestion</title>
  <meta name="description" content="Rapport interne d'analyse quantitative des signaux sur les métaux précieux et industriels — CDG Capital Gestion.">
  {chart_script_tag}
  <style>{CSS}</style>
</head>
<body>

<div class="cover">
  <div class="cover-logo">CDG Capital Gestion · Analyse Quantitative</div>
  <h1>Backtest des Signaux Quantitatifs<br>Métaux Précieux &amp; Industriels</h1>
  <p class="cover-sub">
    Rapport interne d'analyse des signaux de trading systématique sur l'or, l'argent et le cuivre.
    Méthodologie anti-data-mining avec validation walk-forward 3 périodes et tests de significativité statistique.
  </p>
  <div class="cover-meta">
    <span>Date de génération&nbsp;: <strong>{date_str} à {time_str}</strong></span>
    <span>Signaux analysés&nbsp;: <strong>{n_signals}</strong></span>
    <span>Horizons testés&nbsp;: <strong>{n_horizons} (J+1 à J+60)</strong></span>
    <span>Mode&nbsp;: <strong>Données fraîches + backtest historique</strong></span>
    <span>Historique&nbsp;: <strong>{date_min}</strong></span>
    <span>Coût AR&nbsp;: <strong>{TRANSACTION_COST_PCT:.2f} %</strong></span>
  </div>
</div>

<div class="page">

<div class="section">
  <div class="section-title">01 — Données fraîches du jour</div>
  <h2>Snapshot quotidien et signaux de marché</h2>
  {daily_snapshot}
</div>

<div class="section">
  <div class="section-title">02 — Résumé exécutif</div>
  <h2>Vue d'ensemble des signaux</h2>
  {kpi_strip}
  {summary_table}
</div>

<div class="section">
  <div class="section-title">03 — Analyse multi-horizons</div>
  <h2>Heatmap rendement net (%) par signal et horizon</h2>
  <p style="color:var(--muted);font-size:12px;margin-bottom:16px">
    Rendement net après déduction du coût aller-retour de {TRANSACTION_COST_PCT:.2f} %.
    Vert = alpha positif · Rouge = alpha négatif · Gris = signal non disponible.
  </p>
  {heatmap}
</div>

<div class="section">
  <div class="section-title">04 — Détail signal par signal</div>
  <h2>Analyse détaillée avec profil de rendement</h2>
  <p style="color:var(--muted);font-size:12px;margin-bottom:20px">
    Chaque carte présente les métriques au meilleur horizon pour le signal.
    La courbe affiche l'évolution du rendement brut, net et de la baseline sur tous les horizons.
  </p>
  {signal_cards}
</div>

<div class="section">
  <div class="section-title">05 — Méthodologie</div>
  <h2>Cadre d'analyse et hypothèses</h2>
  {methodology}
</div>

<div class="footer">
  <strong>CDG Capital Gestion — Usage interne exclusif</strong><br>
  Ce document est généré automatiquement par le moteur de backtest quantitatif.
  Il ne constitue pas un conseil en investissement.<br>
  Rapport généré le {date_str} à {time_str} · Données sources : Yahoo Finance, FRED, SPDR Gold Shares
</div>

</div>
</body>
</html>"""

    Path(output).write_text(html, encoding="utf-8")
    print(f"[OK] Rapport généré -> {output}")


if __name__ == "__main__":
    import sys
    reconf = getattr(sys.stdout, "reconfigure", None)
    if callable(reconf):
      try:
        reconf(encoding="utf-8", errors="replace")
      except Exception:
        pass
    build_report()
