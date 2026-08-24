import os
import sys
import argparse
import webbrowser
from datetime import datetime
from pathlib import Path


def run_pipeline(skip_download: bool = False, open_browser: bool = False):
    reconf = getattr(sys.stdout, "reconfigure", None)
    if callable(reconf):
        try:
            reconf(encoding="utf-8", errors="replace")
        except Exception:
            pass

    print("\n" + "=" * 80)
    print("  CDG CAPITAL GESTION (CASABLANCA) — POLE GESTION D'ACTIFS & RECHERCHE QUANT")
    print("  Mandat Métaux (Or/Ag/Cu/Cash)")
    print(f"  Date d'exécution : {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 80 + "\n")

    print("[1/5] Ingestion & actualisation des donnees de marche...")
    data_file = Path("metaux_daily_data.csv")
    if skip_download:
        if not data_file.exists():
            print(f"  [AVERTISSEMENT] {data_file} introuvable localement. Téléchargement forcé.")
            import data_collector
            data_collector.run(save_csv=True)
        else:
            print(f"  [INFO] Utilisation des données locales ({data_file.name}).")
    else:
        try:
            import data_collector
            data_collector.run(save_csv=True)
            print("  [OK] Données actualisées avec succès.")
        except Exception as e:
            print(f"  [ERREUR] Échec de la collecte en ligne : {e}")
            if data_file.exists():
                print(f"  [REPLI] Utilisation du fichier local existant : {data_file.name}")
            else:
                raise

    print("\n[2/5] Calcul des signaux et backtest...")
    import backtest
    backtest_results = backtest.run_backtest(data_file=str(data_file))
    print(f"  [OK] Backtest terminé ({len(backtest_results)} configurations testées).")

    print("\n[3/5] Allocation tactique, simulation de portefeuille et Stress-Tests...")
    import portfolio_engine
    ts, metrics, risk_metrics, stress_results, fx_results = portfolio_engine.run_full_portfolio_analysis()
    print("  [OK] Simulation de portefeuille terminée.")

    print("\n[4/5] Génération du rapport de backtest HTML...")
    import backtest_report
    backtest_report.build_report(results_file="backtest_results.csv", output="backtest_report.html")

    print("\n[5/5] Génération du tableau de bord...")
    import dashboard
    dashboard.generate_manager_dashboard_html(output_file="dashboard.html")

    print("\n" + "=" * 80)
    print("  SYNTHÈSE DES LIVRABLES GÉNÉRÉS")
    print("=" * 80)
    print("  - dashboard.html")
    print("  - backtest_report.html")
    print("  - portfolio_timeseries.csv")
    print("  - portfolio_backtest_results.csv")
    print("  - backtest_results.csv")
    print("=" * 80 + "\n")

    if open_browser:
        print("  Ouverture des livrables dans le navigateur...")
        dash_path = Path("dashboard.html").resolve().as_uri()
        rep_path = Path("backtest_report.html").resolve().as_uri()
        webbrowser.open(dash_path)
        webbrowser.open(rep_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline Quantitatif Métaux — CDG Capital")
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Ignore le téléchargement web et utilise les données locales existantes",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Ouvre automatiquement les rapports HTML générés dans le navigateur",
    )
    args = parser.parse_args()
    run_pipeline(skip_download=args.skip_download, open_browser=args.open)
