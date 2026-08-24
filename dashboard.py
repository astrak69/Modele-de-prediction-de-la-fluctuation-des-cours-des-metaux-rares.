import json
import math
import webbrowser
from pathlib import Path
import numpy as np
import pandas as pd
from datetime import datetime

from portfolio_engine import (
    load_and_enrich_data,
    compute_daily_scores_and_weights,
    run_portfolio_backtest,
    compute_risk_metrics,
    run_stress_tests,
    simulate_moroccan_fx_context,
    BENCHMARK_WEIGHTS,
    TACTICAL_CONSTRAINTS,
    SIGNAL_RULES,
)


def generate_manager_dashboard_html(output_file: str = "dashboard.html"):
    df = load_and_enrich_data()
    enriched = compute_daily_scores_and_weights(df)
    ts, metrics = run_portfolio_backtest(enriched)
    risk = compute_risk_metrics(ts)
    
    latest_weights = {
        "gold": ts["weight_gold"].iloc[-1],
        "silver": ts["weight_silver"].iloc[-1],
        "copper": ts["weight_copper"].iloc[-1],
        "cash": ts["weight_cash"].iloc[-1],
    }
    stress = run_stress_tests(latest_weights)
    fx = simulate_moroccan_fx_context(ts)

    dates = [d.strftime("%Y-%m-%d") for d in ts.index]
    nav_strat = [round(v, 2) for v in ts["nav_strategy"].tolist()]
    nav_bm = [round(v, 2) for v in ts["nav_benchmark"].tolist()]
    dd_strat = [round(v, 2) for v in ts["dd_strategy"].tolist()]
    dd_bm = [round(v, 2) for v in ts["dd_benchmark"].tolist()]

    w_g = [round(v * 100, 1) for v in ts["weight_gold"].tolist()]
    w_s = [round(v * 100, 1) for v in ts["weight_silver"].tolist()]
    w_c = [round(v * 100, 1) for v in ts["weight_copper"].tolist()]
    w_k = [round(v * 100, 1) for v in ts["weight_cash"].tolist()]

    last_row = enriched.iloc[-1]
    active_signals_today = []
    for metal, rules in SIGNAL_RULES.items():
        for r in rules:
            col = r["col"]
            if col in enriched.columns and pd.notna(last_row.get(col)):
                val = last_row[col]
                is_act = r["cond"](val)
                if is_act:
                    active_signals_today.append({
                        "metal": metal.upper(),
                        "name": r["name"],
                        "col": col,
                        "value": round(val, 2),
                        "direction": "HAUSSIER (LONG)" if r["dir"] > 0 else "BAISSIER (SHORT)",
                        "weight": r["weight"],
                    })

    ts_annual = ts.copy()
    ts_annual["year"] = ts_annual.index.year
    annual_summary = []
    for y, grp in ts_annual.groupby("year"):
        r_strat = ((1 + grp["strat_net_return"]).prod() - 1) * 100
        r_bm = ((1 + grp["bm_return"]).prod() - 1) * 100
        annual_summary.append({
            "year": y,
            "strat_%": round(r_strat, 2),
            "bm_%": round(r_bm, 2),
            "alpha_%": round(r_strat - r_bm, 2),
        })

    last_date_str = ts.index[-1].strftime("%d/%m/%Y")

    html_content = f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <title>CDG Capital — Desk Métaux & Allocation Tactique</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg-base: #0c0f17;
      --bg-card: #141926;
      --bg-card-hover: #1b2234;
      --border: #232d42;
      --accent: #2563eb;
      --accent-gold: #f59e0b;
      --accent-silver: #94a3b8;
      --accent-copper: #d97706;
      --green: #10b981;
      --red: #ef4444;
      --text: #f1f5f9;
      --text-muted: #8b9bb4;
      --font: 'Inter', sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ background: var(--bg-base); color: var(--text); font-family: var(--font); padding: 24px; }}
    .container {{ max-width: 1400px; margin: 0 auto; }}
    
    header {{ display: flex; justify-content: space-between; align-items: center; padding-bottom: 20px; border-bottom: 1px solid var(--border); margin-bottom: 24px; }}
    .logo-box h1 {{ font-size: 22px; font-weight: 700; color: #fff; display: flex; align-items: center; gap: 10px; }}
    .logo-box p {{ font-size: 13px; color: var(--text-muted); margin-top: 4px; }}
    .date-badge {{ background: #1e293b; padding: 6px 14px; border-radius: 20px; font-size: 13px; font-weight: 600; color: var(--accent-gold); border: 1px solid #334155; }}

    .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 24px; }}
    .kpi-card {{ background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 18px; position: relative; overflow: hidden; }}
    .kpi-card::before {{ content: ''; position: absolute; top: 0; left: 0; width: 4px; height: 100%; background: var(--accent); }}
    .kpi-card.gold::before {{ background: var(--accent-gold); }}
    .kpi-card.green::before {{ background: var(--green); }}
    .kpi-card.red::before {{ background: var(--red); }}
    .kpi-title {{ font-size: 12px; text-transform: uppercase; color: var(--text-muted); font-weight: 600; letter-spacing: 0.5px; }}
    .kpi-val {{ font-size: 26px; font-weight: 700; margin: 8px 0 4px 0; font-family: var(--font-mono); }}
    .kpi-sub {{ font-size: 12px; color: var(--text-muted); }}

    .grid-2 {{ display: grid; grid-template-columns: 2fr 1fr; gap: 20px; margin-bottom: 24px; }}
    .grid-equal {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px; }}
    .card {{ background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; }}
    .card-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }}
    .card-title {{ font-size: 15px; font-weight: 600; color: #fff; }}

    .alloc-bar-container {{ margin-bottom: 16px; }}
    .alloc-row {{ display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 6px; font-weight: 500; }}
    .bar-bg {{ background: #1e293b; height: 10px; border-radius: 5px; overflow: hidden; }}
    .bar-fill {{ height: 100%; border-radius: 5px; transition: width 0.5s; }}

    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th {{ text-align: left; padding: 10px; background: #1a2234; color: var(--text-muted); font-weight: 600; border-bottom: 1px solid var(--border); }}
    td {{ padding: 10px; border-bottom: 1px solid var(--border); }}
    tr:last-child td {{ border-bottom: none; }}
    
    .badge {{ display: inline-block; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }}
    .badge-long {{ background: rgba(16, 185, 129, 0.2); color: var(--green); border: 1px solid rgba(16, 185, 129, 0.4); }}
    .badge-short {{ background: rgba(239, 68, 68, 0.2); color: var(--red); border: 1px solid rgba(239, 68, 68, 0.4); }}
  </style>
</head>
<body>
<div class="container">
  <header>
    <div class="logo-box">
      <h1>🏛️ CDG CAPITAL GESTION — DESK MÉTAUX</h1>
      <p>Moteur d'Allocation Tactique & Analyse des Risques Réglementaires (AMMC / Bâle III)</p>
    </div>
    <div class="date-badge">📅 Données au : {last_date_str}</div>
  </header>

  <div class="kpi-grid">
    <div class="kpi-card green">
      <div class="kpi-title">Alpha Annuel Net</div>
      <div class="kpi-val" style="color:var(--green)">+{metrics['alpha_annuel_%']:.2f} %</div>
      <div class="kpi-sub">CAGR Strat : {metrics['cagr_strategy_%']:.2f}% | BM : {metrics['cagr_benchmark_%']:.2f}%</div>
    </div>
    <div class="kpi-card gold">
      <div class="kpi-title">Ratio de Sharpe</div>
      <div class="kpi-val" style="color:var(--accent-gold)">{metrics['sharpe_strategy']:.3f}</div>
      <div class="kpi-sub">Benchmark : {metrics['sharpe_benchmark']:.3f} (Rf = 3.0%)</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-title">Ratio d'Information</div>
      <div class="kpi-val">{metrics['ratio_information']:.3f}</div>
      <div class="kpi-sub">Tracking Error : {metrics['tracking_error_%']:.2f}%</div>
    </div>
    <div class="kpi-card red">
      <div class="kpi-title">VaR Bâle III (99% - 10j)</div>
      <div class="kpi-val" style="color:var(--red)">{risk['var_reglementaire_99_10j_%']:.2f} %</div>
      <div class="kpi-sub">VaR 1j 95% : {risk['var_historique_95_1j_%']:.2f}% | CVaR : {risk['expected_shortfall_cvar_95_1j_%']:.2f}%</div>
    </div>
  </div>

  <div class="grid-2">
    <div class="card">
      <div class="card-header">
        <div class="card-title">📈 Performance Comparée — Stratégie Tactique vs Benchmark Stratégique (Base 100)</div>
      </div>
      <canvas id="chartNav" height="110"></canvas>
    </div>

    <div class="card">
      <div class="card-header">
        <div class="card-title">🎯 Allocation Tactique Cible du Jour</div>
      </div>
      <div class="alloc-bar-container">
        <div class="alloc-row">
          <span>🥇 OR (Front)</span>
          <span style="color:var(--accent-gold)"><b>{latest_weights['gold']*100:.1f} %</b> (Neutre: 49%)</span>
        </div>
        <div class="bar-bg"><div class="bar-fill" style="width: {latest_weights['gold']*100}%; background: var(--accent-gold);"></div></div>
      </div>

      <div class="alloc-bar-container">
        <div class="alloc-row">
          <span>🥈 ARGENT</span>
          <span style="color:var(--accent-silver)"><b>{latest_weights['silver']*100:.1f} %</b> (Neutre: 16%)</span>
        </div>
        <div class="bar-bg"><div class="bar-fill" style="width: {latest_weights['silver']*100}%; background: var(--accent-silver);"></div></div>
      </div>

      <div class="alloc-bar-container">
        <div class="alloc-row">
          <span>🥉 CUIVRE</span>
          <span style="color:var(--accent-copper)"><b>{latest_weights['copper']*100:.1f} %</b> (Neutre: 27%)</span>
        </div>
        <div class="bar-bg"><div class="bar-fill" style="width: {latest_weights['copper']*100}%; background: var(--accent-copper);"></div></div>
      </div>

      <div class="alloc-bar-container">
        <div class="alloc-row">
          <span>💵 CASH (TMP BAM)</span>
          <span><b>{latest_weights['cash']*100:.1f} %</b> (Neutre: 8%)</span>
        </div>
        <div class="bar-bg"><div class="bar-fill" style="width: {latest_weights['cash']*100}%; background: #3b82f6;"></div></div>
      </div>

      <div style="font-size:12px; color:var(--text-muted); margin-top:14px; line-height:1.4;">
        <b>Contraintes AMMC / CDG :</b> Or [30%-65%], Argent [8%-25%], Cuivre [15%-40%], Cash Min 2%.
      </div>
    </div>
  </div>

  <div class="card" style="margin-bottom:24px;">
    <div class="card-header">
      <div class="card-title">⚖️ Évolution Dynamique des Pondérations Tactiques</div>
    </div>
    <canvas id="chartWeights" height="70"></canvas>
  </div>

  <div class="grid-equal">
    <div class="card">
      <div class="card-header">
        <div class="card-title">⚡ Signaux Actifs au {last_date_str}</div>
      </div>
      <table>
        <thead>
          <tr>
            <th>Métal</th>
            <th>Signal Déclenché</th>
            <th>Direction</th>
            <th>Z-Score</th>
          </tr>
        </thead>
        <tbody>
          {''.join(f"<tr><td><b>{s['metal']}</b></td><td>{s['name']}</td><td><span class='badge {'badge-long' if 'LONG' in s['direction'] else 'badge-short'}'>{s['direction']}</span></td><td style='font-family:var(--font-mono)'>{s['value']:+.2f}</td></tr>" for s in active_signals_today) if active_signals_today else "<tr><td colspan='4' style='color:var(--text-muted);text-align:center;'>Aucun signal extrême actif aujourd'hui (Allocation neutre maintenue)</td></tr>"}
        </tbody>
      </table>
    </div>

    <div class="card">
      <div class="card-header">
        <div class="card-title">🌪️ Stress-Tests Macroéconomiques</div>
      </div>
      <table>
        <thead>
          <tr>
            <th>Scénario de Choc</th>
            <th>Impact Strat</th>
            <th>Impact BM</th>
            <th>Protection</th>
          </tr>
        </thead>
        <tbody>
          {''.join(f"<tr><td><b>{st['scenario'].split('(')[0]}</b></td><td style='color:{'#10b981' if st['impact_strategie_%'] > 0 else '#ef4444'}'>{st['impact_strategie_%']:+.2f}%</td><td style='color:{'#10b981' if st['impact_benchmark_%'] > 0 else '#ef4444'}'>{st['impact_benchmark_%']:+.2f}%</td><td><b>{st['protection_relative_%']:+.2f}%</b></td></tr>" for st in stress)}
        </tbody>
      </table>
    </div>
  </div>

  <div class="grid-equal">
    <div class="card">
      <div class="card-header">
        <div class="card-title">🇲🇦 Analyse FX USD/MAD (Contexte BAM)</div>
      </div>
      <table>
        <tr><td>Statut Réglementaire</td><td><b>{fx['statut_reglementaire_ammc']}</b></td></tr>
        <tr><td>Régime de Change</td><td>{fx['regime_change_bam']}</td></tr>
        <tr><td>Coût Couverture Forward FX</td><td><b>{fx['cout_couverture_forward_annuel_%']:.2f} % / an</b></td></tr>
        <tr><td>CAGR en MAD (Non Couvert)</td><td><b>{fx['cagr_en_mad_non_couvert_%']:.2f} %</b></td></tr>
        <tr><td>CAGR en MAD (Couvert 100%)</td><td><b>{fx['cagr_en_mad_couvert_100_%']:.2f} %</b></td></tr>
        <tr><td>Recommandation CDG</td><td style="color:var(--accent-gold)"><b>{fx['recommandation_cdg']}</b></td></tr>
      </table>
    </div>

    <div class="card">
      <div class="card-header">
        <div class="card-title">📅 Rendements Annuels Comparés</div>
      </div>
      <table>
        <thead>
          <tr><th>Année</th><th>Stratégie</th><th>Benchmark</th><th>Alpha Net</th></tr>
        </thead>
        <tbody>
          {''.join(f"<tr><td><b>{a['year']}</b></td><td style='color:{'#10b981' if a['strat_%']>0 else '#ef4444'}'>{a['strat_%']:+.2f}%</td><td style='color:{'#10b981' if a['bm_%']>0 else '#ef4444'}'>{a['bm_%']:+.2f}%</td><td style='font-weight:700;color:{'#10b981' if a['alpha_%']>0 else '#ef4444'}'>{a['alpha_%']:+.2f}%</td></tr>" for a in annual_summary)}
        </tbody>
      </table>
    </div>
  </div>

</div>

<script>
  const dates = {json.dumps(dates)};
  const navStrat = {json.dumps(nav_strat)};
  const navBm = {json.dumps(nav_bm)};

  new Chart(document.getElementById('chartNav'), {{
    type: 'line',
    data: {{
      labels: dates,
      datasets: [
        {{ label: 'Stratégie Tactique CDG', data: navStrat, borderColor: '#10b981', borderWidth: 2, pointRadius: 0, tension: 0.1 }},
        {{ label: 'Benchmark Stratégique (49/16/27/8)', data: navBm, borderColor: '#64748b', borderWidth: 1.5, borderDash: [4, 4], pointRadius: 0, tension: 0.1 }}
      ]
    }},
    options: {{
      responsive: true,
      plugins: {{ legend: {{ labels: {{ color: '#e2e8f0' }} }} }},
      scales: {{
        x: {{ grid: {{ color: '#1e293b' }}, ticks: {{ color: '#64748b', maxTicksLimit: 8 }} }},
        y: {{ grid: {{ color: '#1e293b' }}, ticks: {{ color: '#64748b' }} }}
      }}
    }}
  }});

  new Chart(document.getElementById('chartWeights'), {{
    type: 'line',
    data: {{
      labels: dates,
      datasets: [
        {{ label: 'Or %', data: {json.dumps(w_g)}, borderColor: '#f59e0b', backgroundColor: 'rgba(245, 158, 11, 0.2)', fill: true, pointRadius: 0 }},
        {{ label: 'Argent %', data: {json.dumps(w_s)}, borderColor: '#94a3b8', backgroundColor: 'rgba(148, 163, 184, 0.2)', fill: true, pointRadius: 0 }},
        {{ label: 'Cuivre %', data: {json.dumps(w_c)}, borderColor: '#d97706', backgroundColor: 'rgba(217, 119, 6, 0.2)', fill: true, pointRadius: 0 }},
        {{ label: 'Cash %', data: {json.dumps(w_k)}, borderColor: '#3b82f6', backgroundColor: 'rgba(59, 130, 246, 0.2)', fill: true, pointRadius: 0 }}
      ]
    }},
    options: {{
      responsive: true,
      plugins: {{
        legend: {{ labels: {{ color: '#e2e8f0' }} }}
      }},
      scales: {{
        x: {{ grid: {{ color: '#1e293b' }}, ticks: {{ color: '#64748b', maxTicksLimit: 8 }} }},
        y: {{ grid: {{ color: '#1e293b' }}, ticks: {{ color: '#64748b' }} }}
      }}
    }}
  }});
</script>
</body>
</html>
"""
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"[OK] Dashboard Gérant généré avec succès -> {output_file}")


def print_cli_dashboard():
    df = load_and_enrich_data()
    enriched = compute_daily_scores_and_weights(df)
    ts, metrics = run_portfolio_backtest(enriched)
    risk = compute_risk_metrics(ts)
    latest_weights = {
        "gold": ts["weight_gold"].iloc[-1],
        "silver": ts["weight_silver"].iloc[-1],
        "copper": ts["weight_copper"].iloc[-1],
        "cash": ts["weight_cash"].iloc[-1],
    }

    print("\n" + "=" * 80)
    print("  TABLEAU DE BORD GÉRANT — CDG CAPITAL GESTION")
    print(f"  Date du jour : {ts.index[-1].strftime('%d/%m/%Y')}")
    print("=" * 80)
    print("\n  ALLOCATION TACTIQUE CIBLE :")
    print(f"    - OR     : {latest_weights['gold']*100:.1f} %  (Neutre : 49.0 % | Tilt : {(latest_weights['gold']-0.49)*100:+.1f} %)")
    print(f"    - ARGENT : {latest_weights['silver']*100:.1f} %  (Neutre : 16.0 % | Tilt : {(latest_weights['silver']-0.16)*100:+.1f} %)")
    print(f"    - CUIVRE : {latest_weights['copper']*100:.1f} %  (Neutre : 27.0 % | Tilt : {(latest_weights['copper']-0.27)*100:+.1f} %)")
    print(f"    - CASH   : {latest_weights['cash']*100:.1f} %  (Neutre :  8.0 % | Tilt : {(latest_weights['cash']-0.08)*100:+.1f} %)")
    print("\n  MÉTRIQUES DE GESTION :")
    print(f"    - Alpha Annuel          : {metrics['alpha_annuel_%']:+.2f} % / an")
    print(f"    - Ratio de Sharpe       : {metrics['sharpe_strategy']:.3f} (Benchmark : {metrics['sharpe_benchmark']:.3f})")
    print(f"    - VaR Réglementaire 10j : {risk['var_reglementaire_99_10j_%']:.2f} %")
    print("=" * 80)


if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print_cli_dashboard()
    generate_manager_dashboard_html("dashboard.html")
