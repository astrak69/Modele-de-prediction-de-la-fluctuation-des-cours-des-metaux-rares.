📑 NOTE MÉTHODOLOGIQUE & DE CADRAGE INSTITUTIONNEL
Pôle Gestion d'Actifs — CDG Capital Casablanca
Direction de la Recherche Quantitative & Allocation d'Actifs
Mandat de GestionPortefeuille Multi-Matières Premières (Métaux Précieux & Industriels)Benchmark StratégiqueOr (49 %) / Argent (16 %) / Cuivre (27 %) / Cash TMP BAM (8 %)Univers d'InvestissementContrats Futures Front-Month (COMEX / CME), ETFs Physiques sous-jacentsPériode d'Analyse2021 – 2026 (5 ans d'historique journalier)Cadre PrudentielRéglementation AMMC (OPCVM Diversifiés) & Standards Bâle IIIDevise de RéférenceUSD (Conversion et couverture de change MAD documentée)

1. Thèse d'Investissement & Construction du Benchmark
1.1 Rôle Économique des Composantes
1. Or (49 %) — Actif Monétaire & Réserve de Valeur : 
• Corrélation historiquement négative avec les taux réels US 10 ans.
• Couverture contre l'inflation non anticipée, la dépréciation du dollar et les risques géopolitiques systémiques (flight-to-safety).
2. Argent (16 %) — Vecteur Hybride (Monétaire & Industriel) : 
• Forte élasticité aux cycles économiques grâce à ses applications industrielles croissantes (photovoltaïque, électronique de puissance, véhicules électriques).
• Bêta plus élevé que l'or lors des phases d'expansion haussière des métaux.
3. Cuivre (27 %) — Baromètre Cyclique & Électrification Globale : 
• Indispensable aux infrastructures électriques mondiales, réseaux d'énergie renouvelable et urbanisation des pays émergents.
• Forte corrélation avec les indicateurs manufacturiers globaux (INDPRO, PMI).
4. Cash / TMP (8 %) — Buffer de Liquidité & Marge de Trésorerie : 
• Rémunéré au Taux Moyen Pondéré (TMP) de Bank Al-Maghrib (~3,0 % annualisé).
• Permet d'absorber les appels de marge sur futures et d'ajuster les pondérations sans contrainte de liquidité.
2. Architecture Multi-Signaux & Modélisation Quantitative
2.1 Sources de Données Ingestées
• Marchés Financiers (Yahoo Finance) : Cours de clôture des contrats futures front (GC=F, SI=F, HG=F), indice Dollar (DX-Y.NYB), indice de volatilité implicite de l'or (^GVZ), volumes des ETFs physiques (GLD, SLV, CPER).
• Données Macroéconomiques US (FRED St-Louis Fed) :
◦ Taux réels 10 ans TIPS : DFII10
◦ Anticipations d'inflation 10 ans Breakeven : T10YIE
◦ Rendement 10Y US Treasury : DGS10
◦ Indice de Production Industrielle : INDPRO
• Données de Positionnement des Acteurs (CFTC Socrata API) : Données hebdomadaires Commitment of Traders (COT) : positions nettes des gérants spéculateurs (Managed Money Long - Short).
• Flux Physiques Institutionnels : Avoirs officiels en tonnes d'or du trust SPDR Gold Shares.
2.2 Normalisation & Détection Statistique
Tous les indicateurs sont convertis en z-scores glissants sur une fenêtre de 60 jours ouvrés :
z_t = (x_t − μ_60,t) / σ_60,t
Les signaux individuels sont déclenchés lors de franchissements de seuils extrêmes (|z_t| ≥ 1,5 ou |z_t| ≥ 2,0), éliminant le bruit de marché.
3. Allocation Tactique Dynamique & Contraintes de Gestion
3.1 Détermination du Score Composite
Pour chaque actif i ∈ {Or, Argent, Cuivre}, un score composite S(i,t) ∈ [-1,0 ; +1,0] est calculé en agrégeant les signaux actifs pondérés par leur pertinence statistique :
S(i,t) = clip( 2,0 × [ Σk 𝟙(k,t) · dir_k · w_k ] / Σk w_k , −1,0 , +1,0 )
3.2 Application des Contraintes Réglementaires (AMMC & CDG Capital)
Les poids cibles sont ajustés selon la règle :
w(i,t)_cible = clip( w_i_benchmark + S(i,t) · Tilt_max,i , w_min,i , w_max,i )
MétalPoids BenchmarkBorne MinBorne MaxTilt Max AutoriséOr49,0 %30,0 %65,0 %±15,0 %Argent16,0 %8,0 %25,0 %±8,0 %Cuivre27,0 %15,0 %40,0 %±10,0 %Cash8,0 %2,0 %25,0 %—Le cash résiduel est contraint à un minimum incompressible de 2 % pour garantir la liquidité quotidienne du fonds.


4. Résultats Empiriques & Performance du Backtest
4.1 Ratios de Performance Comparée
La simulation historique intègre un décalage systématique de 1 jour (T+1) pour neutraliser tout biais d'anticipation (look-ahead bias), ainsi qu'une commission institutionnelle de 5 bps par mouvement de turnover.
MétriqueStratégie TactiqueBenchmarkCommentaire de GestionCAGR (Rendement annuel)15,64 %14,43 %Surperformance annuelle nette de +121 bps.Volatilité Annualisée18,69 %18,68 %Profil de volatilité strictement identique.Ratio de Sharpe0,6760,612Amélioration notable du rendement par unité de risque.Ratio de Sortino0,8410,760Excellente protection sur la volatilité baissière.Maximum Drawdown-22,26 %-22,97 %Atténuation des phases de purge de marché.Ratio de Calmar0,7030,628Rendement annualisé supérieur rapporté au pire drawdown.Tracking Error1,22 %—Fidélité au mandat de base, sans dérive excessive.Ratio d'Information (IR)0,995—Qualité d'alpha institutionnelle exceptionnelle (IR ≈ 1).Taux de Succès Quotidien37,44 %—Stratégie de type trend/convexité (gains asymétriques).5. Dispositif de Gestion des Risques & Stress-Testing
5.1 Mesures de Valeur en Risque (Standards Bâle III)
• VaR Historique 95 % (1 jour) : -1,92 %
• VaR Historique 99 % (1 jour) : -2,88 %
• VaR Réglementaire 99 % (10 jours Bâle) : -9,11 %
• Expected Shortfall / CVaR 95 % (1 jour) : -2,52 %
• Expected Shortfall / CVaR 99 % (1 jour) : -3,52 %
5.2 Matrice de Stress-Testing Macroéconomique
Scénario MacroéconomiqueHypothèse de Choc de MarchéImpact StratégieImpact BenchmarkProtection Relative1. Choc Déflationniste / Dollar Spike (Mars 2020)Flambée DXY (+6 %), Or -4 %, Argent -15 %, Cuivre -12 %-7,60 %-7,60 %0,00 %2. Choc Stagflationniste (Type 2022)Taux réels négatifs, Or +8 %, Argent +5 %, Cuivre -6 %+3,10 %+3,10 %0,00 %3. Récession Industrielle (Crash Chinois)Cuivre -18 %, Argent -8 %, Or +3 %-4,67 %-4,67 %0,00 %4. Crise Géopolitique (Flight-to-Safety)Ruée sur l'or (+12 %), Argent +8 %, Cuivre -2 %+6,62 %+6,62 %0,00 %6. Risque de Change USD / MAD pour l'Investisseur Marocain
Les actifs sous-jacents étant cotés en USD, un fonds géré à Casablanca est exposé à la parité USD/MAD.
• Régime de Change BAM : Panier de référence composé à 60 % d'EUR et 40 % d'USD, avec une bande de fluctuation de ±5 %.
• Coût de Couverture Forward : Le différentiel de taux d'intérêt (spread Bank Al-Maghrib TMP vs Fed Funds) engendre un coût de portage de couverture de change estimé à environ 1,75 % / an.
• Recommandation CDG Capital : Mise en œuvre d'une couverture dynamique partielle (50 % passive), permettant de réduire la volatilité globale du portefeuille en MAD sans subir la totalité du coût de traînée du contrat Forward.

CDG Capital — Direction Gestion d'Actifs
Document rédigé pour le Comité de Gestion et la Direction des Risques.

CDG Capital — Note Méthodologique Institutionnelle

Page 5 / 5   —   Document rédigé pour le Comité de Gestion et la Direction des Risques

