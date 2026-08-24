# CDG CAPITAL GESTION

## Pôle Gestion d'Actifs & Recherche Quantitative

### Projet de recherche & moteur d'allocation tactique
#### Mandat Métaux Précieux & Industriels

`Python 3.10+` &nbsp;•&nbsp; `CDG Capital — Casablanca` &nbsp;•&nbsp; `Statut : Livrable Institutionnel`

Ce projet implémente un système institutionnel complet de recherche quantitative, d'allocation tactique dynamique et de gestion des risques pour un portefeuille multi-matières premières :

#### Or — Neutre : 49 %
Moteur de préservation du capital, valeur refuge et actif sensible à l'évolution des taux réels.

#### Argent — Neutre : 16 %
Actif hybride, à la fois monétaire et industriel, exposé à la transition énergétique, notamment à l'électronique et au photovoltaïque.

#### Cuivre — Neutre : 27 %
Baromètre de l'activité économique mondiale, de l'industrialisation et de l'électrification.

#### Cash / TMP Bank Al-Maghrib — Neutre : 8 %
Marge de sécurité, réserve de liquidité et outil de pilotage du risque global.

---

## 1. Synthèse des performances & ratios institutionnels

| Indicateur financier | Stratégie tactique CDG | Benchmark Buy-and-Hold | Écart / Alpha |
|---|:---:|:---:|:---:|
| Rendement annuel composé — CAGR | 15,64 % | 14,43 % | +1,21 % / an |
| Alpha de Jensen ajusté du risque | +1,23 % | 0,00 % | +1,23 % |
| Volatilité annualisée | 18,69 % | 18,68 % | +0,01 % |
| Ratio de Sharpe — Rf = 3,0 % | 0,676 | 0,612 | +0,064 |
| Ratio de Sortino — risque baissier | 0,841 | 0,760 | +0,081 |
| Maximum Drawdown | -22,26 % | -22,97 % | +0,71 % d'atténuation |
| Ratio de Calmar | 0,703 | 0,628 | +0,075 |
| Bêta vs benchmark | 0,998 | 1,000 | Neutre |
| Tracking Error | 1,22 % | — | Risque maîtrisé |
| Ratio d'information — IR | 0,995 | — | Qualité d'alpha élevée |
| Turnover annuel moyen | 508,3 % | 0,0 % | Environ 2,0 % / jour |
| Coût total de rebalancement | 25,4 bps / an | 0,0 bps | Intégré en net |

Note : tous les résultats sont présentés nets des coûts de turnover, estimés à 5 bps aller-retour par transaction.

---

## 2. Démarrage rapide & exécution en un clic

### A. Prérequis & installation

```bash
# 1. Cloner ou ouvrir le dossier du projet
cd metaux_project

# 2. Installer les dépendances
pip install -r requirements.txt
```

### B. Lancement du pipeline complet

Pour exécuter la chaîne de traitement de bout en bout — collecte des données, génération des signaux, construction du portefeuille, analyse des risques et production des rapports — utiliser la commande suivante :

```bash
# Exécution complète avec ouverture automatique des tableaux de bord
python run_pipeline.py --open

# Recalcul rapide sur l'historique local, sans retéléchargement des données
python run_pipeline.py --skip-download
```

---

## 3. Livrables & tableaux de bord

| Livrable | Description | Format |
|---|---|:---:|
| [`dashboard.html`](dashboard.html) | Tableau de bord de gestion : recommandation tactique du jour, allocation actualisée, attribution de performance, simulateur de stress tests et suivi du risque de change USD/MAD. | Web interactif — Chart.js |
| [`backtest_report.html`](backtest_report.html) | Rapport quantitatif exhaustif : analyse individuelle de chaque signal à 1, 5, 10, 20 et 60 jours, tests de significativité statistique (valeur p, statistique t, bootstrap) et validation walk-forward. | Web interactif |
| [`NOTE_METHODOLOGIQUE_CDG.md`](NOTE_METHODOLOGIQUE_CDG.md) | Note méthodologique institutionnelle : document financier complet destiné au Comité d'Investissement. | Markdown / PDF |
| [`portfolio_timeseries.csv`](portfolio_timeseries.csv) | Historique quotidien complet des valeurs liquidatives, drawdowns, poids tactiques et rendements. | CSV |
| [`portfolio_backtest_results.csv`](portfolio_backtest_results.csv) | Tableau de synthèse de l'ensemble des métriques institutionnelles. | CSV |

---

## 4. Architecture du projet

```text
metaux_project/
│
├── README.md                      # Guide d'accueil et synthèse des performances
├── NOTE_METHODOLOGIQUE_CDG.md     # Note financière et réglementaire CDG Capital
├── requirements.txt               # Dépendances Python
├── .gitignore                     # Exclusion des fichiers temporaires
├── run_pipeline.py                # Orchestrateur maître en un clic
│
├── data_collector.py              # Ingestion multi-sources : Yahoo Finance, FRED, CFTC
├── cot_collector.py               # Connecteur API CFTC — Commitments of Traders
├── backtest.py                    # Moteur d'évaluation statistique des signaux
├── portfolio_engine.py            # Moteur d'allocation, VaR, stress tests et module FX
├── backtest_report.py             # Moteur de rendu du rapport statistique HTML
└── dashboard.py                   # Moteur de rendu du tableau de bord de gestion HTML
```

---

## 5. Cadre de gestion des risques & réglementation

### 5.1 Contraintes AMMC / CDG Capital

- Règle stricte de positions longues uniquement, sans vente à découvert.

Bornes d'allocation strictes :

| Actif | Borne minimale | Borne maximale | Écart tactique maximal |
|---|:---:|:---:|:---:|
| Or | 30 % | 65 % | ±15 % |
| Argent | 8 % | 25 % | ±8 % |
| Cuivre | 15 % | 40 % | ±10 % |
| Cash / TMP | 2 % | 25 % | Variable d'ajustement |

### 5.2 Métriques de risque — VaR & Bâle III

- VaR 95 % — 1 jour : -1,92 %
- VaR 99 % — 1 jour : -2,88 %
- VaR réglementaire 99 % — 10 jours, approche Bâle : -9,11 %
- Expected Shortfall / CVaR 95 % : -2,52 %

### 5.3 Module de change USD/MAD

Le système intègre un module de suivi du risque de change USD/MAD, tenant compte de la structure du panier de Bank Al-Maghrib, composé de :

- 60 % EUR
- 40 % USD

Le module permet également une analyse comparative entre :

- un portefeuille non couvert contre le risque de change ;
- un portefeuille couvert via contrats forward FX.

---

## CDG Capital — Direction Gestion d'Actifs

— Recherche Quantitative & Stratégie d'Investissement


