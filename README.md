# ⚽ xG & Shooting Profile Analysis

> Analyse de la qualité des tirs et des profils de finisseurs en football  
> à partir des données **StatsBomb Open Data**

**Julie Landrevie — Football Data Analyst**  
*Certifiée Sports Analytics (University of Michigan) · Analyse Vidéo & Data dans le Sport (Université de Lorraine)*

---

## 📌 Présentation du projet

Ce projet analyse la **qualité des tirs** en football à travers le prisme du **xG (expected goals)** — une métrique qui quantifie la probabilité qu'un tir se transforme en but, en fonction de critères comme la position, la technique, ou le contexte du tir.

L'objectif est double :
- **Identifier les finisseurs efficaces** : qui surperforme ou sous-performe par rapport à son xG ?
- **Comprendre les patterns de tir** : d'où viennent les occasions les plus dangereuses, à quel moment du match, avec quelle technique ?

### Pourquoi le xG ?

La conversion brute (buts / tirs) est trop sensible à la variance sur un petit échantillon. Le xG permet de **séparer la qualité des occasions créées de l'efficacité du finisseur**, et d'évaluer les joueurs sur ce qui dépend vraiment d'eux.

---

## 🎯 Fonctionnalités

### 📊 Dashboard Streamlit interactif

| Onglet | Description |
|--------|-------------|
| **Vue d'ensemble** | KPIs globaux, top tireurs, répartition par résultat et partie du corps |
| **Shot Map** | Tirs positionnés sur le terrain — taille = xG, couleur = résultat |
| **Profil tireur** | xG vs buts réels par joueur, tri dynamique, tableau complet |
| **Overperformance** | Lollipop chart buts − xG, podiums sur/sous-performants |
| **Zones** | Heatmap xG par zone du terrain + statistiques détaillées |
| **Distribution** | Histogramme de qualité des occasions créées |
| **Timeline** | Accumulation xG minute par minute sur un match choisi |
| **Comparaison** | Face-à-face deux joueurs : métriques + shot maps côte à côte |

**3 filtres sidebar :** Compétition → Équipe → Joueur (tout interconnecté)

### 📓 Notebook analytique

Analyse complète en 12 sections sur la **La Liga 2020/2021** :
- Exploration des données et validation
- Shot maps (Barcelona, Atlético Madrid, etc.)
- Profils tireurs : top xG, top finisseurs, top sélecteurs de tir
- Overperformance sur la saison entière
- Heatmaps et zones de danger
- Timeline El Clásico
- Deep dive Messi
- Insights et conclusions

---

## 🗂️ Structure du projet

```
xg-shooting-analysis/
│
├── src/
│   ├── data_loader.py        # Chargement & nettoyage données StatsBomb
│   ├── metrics.py            # Calcul des métriques xG
│   └── viz.py                # Visualisations (shot map, heatmap, timeline...)
│
├── notebooks/
│   └── 01_xg_shooting_analysis.ipynb   # Analyse complète La Liga 2020/21
│
├── data/
│   └── cache/                # Données mises en cache (auto-généré)
│
├── app.py                    # Dashboard Streamlit
├── requirements.txt
└── README.md
```

---

## ⚙️ Installation & Lancement

### Prérequis

- Python 3.9+
- Git

### Installation

```bash
# Cloner le repo
git clone https://github.com/julie-landrevie/xg-shooting-analysis.git
cd xg-shooting-analysis

# Installer les dépendances
pip install -r requirements.txt
```

### Lancer le dashboard

```bash
streamlit run app.py
```

Le dashboard s'ouvre sur `http://localhost:8501`

> **Note :** Le premier chargement d'une compétition télécharge les données StatsBomb (~1-2 min selon le nombre de matchs). Les données sont ensuite mises en cache dans `data/cache/` pour les prochaines sessions.

### Lancer le notebook

```bash
jupyter notebook notebooks/01_xg_shooting_analysis.ipynb
```

---

## 📦 Stack technique

| Catégorie | Outils |
|-----------|--------|
| **Données** | [statsbombpy](https://github.com/statsbomb/statsbombpy) — API Python StatsBomb Open Data |
| **Manipulation** | pandas, numpy |
| **Visualisation terrain** | [mplsoccer](https://mplsoccer.readthedocs.io/) — terrains de foot avec matplotlib |
| **Graphiques** | matplotlib, seaborn |
| **Dashboard** | Streamlit |
| **Notebook** | Jupyter, nbformat |

---

## 📐 Métriques calculées

| Métrique | Définition |
|----------|-----------|
| `xg` | xG total — somme des probabilités de but de chaque tir |
| `xg_per_shot` | xG moyen par tir — qualité de sélection des occasions |
| `overperformance` | Buts − xG — mesure l'efficacité nette du finisseur |
| `on_target_rate` | % de tirs cadrés (Goal ou Saved) |
| `big_chances` | Nombre d'occasions à xG ≥ 0.30 |
| `conversion_rate` | Taux de conversion réel (buts / tirs) |
| `xg_per_match` | xG moyen par match — intensité offensive régulière |

---

## 🌍 Données disponibles

Le projet utilise les **données open source gratuites de StatsBomb**, accessibles via `statsbombpy` sans authentification :

| Compétition | Saisons disponibles |
|-------------|-------------------|
| La Liga | 2020/21, 2019/20 |
| Champions League | 2018/19, 2017/18, 2016/17, 2015/16, 2014/15... |
| WSL (Women's Super League) | 2020/21 |
| EURO | 2020 |
| Coupe du Monde | 2022 (hommes), 2019 (femmes) |
| African Cup of Nations | 2023 |

> La liste complète est accessible via `list_competitions()` dans le module `data_loader.py`.

---

## 💡 Insights clés — La Liga 2020/2021

*(Extraits de l'analyse notebook)*

- **Lionel Messi** accumule le xG le plus élevé de la saison mais affiche une overperformance négative — ses occasions de qualité n'ont pas toutes été converties sur cette saison
- **Barcelona** génère le xG/match le plus élevé du championnat, confirmant une domination offensive structurelle
- **La surface centrale** concentre le plus grand nombre de tirs, mais c'est la zone **penalty / but vide** qui affiche le xG moyen par tir le plus élevé
- La **dernière demi-heure** (60–90') est la tranche horaire la plus dangereuse en termes de xG cumulé sur l'ensemble de la saison

---

## 🚀 Extensions prévues

- [ ] Intégration des **key passes** pour analyser les assistants (xA)
- [ ] Comparaison multi-saisons — évolution d'un joueur dans le temps
- [ ] Analyse des tirs **sous pression** vs tirs libres
- [ ] Intégration **SkillCorner tracking data** pour contextualiser les tirs avec les données de mouvement
- [ ] Export PDF des profils joueurs

---

## 📁 Projets liés

| Projet | Description | Lien |
|--------|-------------|------|
| **MPG Optimizer** | Fantasy football analytics — scoring, optimiseur XI | [→ Repo](https://github.com/julie-landrevie/mpg-optimizer) |
| **Tactical Dashboard** | Pass Network, xG, Pressing, Heatmaps | [→ Repo](https://github.com/julie-landrevie/tactical-dashboard) |
| **World Cup 2026 Predictor** | Prédictions scores & buteurs Coupe du Monde | [→ Repo](https://github.com/julie-landrevie/worldcup-2026-predictor) |

---

## 📧 Contact

**Julie Landrevie**  
📩 julie.landrevie@free.fr  
🎓 Sports Analytics — University of Michigan (Coursera)  
🎓 Analyse Vidéo & Data dans le Sport — Université de Lorraine  
🎓 Dartfish Certified Analyst

---

*Données : [StatsBomb Open Data](https://github.com/statsbomb/open-data) — utilisées conformément à la licence open data StatsBomb.*
