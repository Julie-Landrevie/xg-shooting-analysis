"""
metrics.py — Calculs et métriques xG pour l'analyse des tirs
=============================================================

Ce module transforme les données brutes de tirs en métriques analytiques
prêtes à visualiser ou à intégrer dans un dashboard.

Principe central : xG vs réalité
---------------------------------
Le xG (expected goals) mesure la QUALITÉ d'une occasion.
Un tir à 0.8 xG = 80% de chances de finir en but selon le modèle.

Comparer le xG au nombre de buts réels révèle deux profils :
  - Buts > xG  → joueur surperformant  (finisseur efficace, ou chanceux)
  - Buts < xG  → joueur sous-performant (maladroit, ou malchanceux)

Métriques calculées dans ce module :
  1. Profil tireur          — buts, xG, tirs, conversion, over/underperformance
  2. Profil équipe          — mêmes métriques agrégées par équipe
  3. xG par zone            — découpage du terrain en zones d'analyse
  4. Distribution xG        — qualité des occasions créées vs concédées
  5. Analyse temporelle     — évolution du xG par tranche de match
  6. Métriques avancées     — xG/tir, taux cadrage, big chances

Structure des fonctions :
  Toutes prennent un pd.DataFrame de tirs (issu de data_loader.py)
  et retournent un pd.DataFrame de métriques, prêt à grapher.
"""

import pandas as pd
import numpy as np


# ============================================================
# CONSTANTES — Zones du terrain
# ============================================================
# Le terrain StatsBomb mesure 120 x 80 unités.
# x=0 = ligne de but propre, x=120 = ligne de but adverse
# y=0 = côté gauche, y=80 = côté droit (vu de derrière l'équipe attaquante)
#
# On définit des zones d'attaque (la moitié du terrain adverse, x > 60)

PITCH_LENGTH = 120
PITCH_WIDTH  = 80

# Seuil xG pour qualifier une occasion de "big chance" (grosse occasion)
BIG_CHANCE_XG_THRESHOLD = 0.3

# Seuil de minutes jouées pour inclure un joueur dans les classements
# (évite les doublures avec 1 tir de figurer en tête)
MIN_SHOTS_FOR_RANKING = 5


# ============================================================
# FONCTION 1 : Profil tireur — statistiques par joueur
# ============================================================

def player_shooting_profile(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcule le profil de tir complet pour chaque joueur.

    C'est la métrique centrale du projet : elle permet de comparer
    la performance réelle (buts) à la performance attendue (xG),
    et d'identifier les finisseurs efficaces vs les joueurs malchanceux.

    Args:
        df (pd.DataFrame) : DataFrame de tirs (issu de data_loader.py)

    Returns:
        pd.DataFrame indexé par joueur avec les colonnes :
        - team              : équipe principale du joueur
        - shots             : nombre total de tirs
        - goals             : buts réels
        - xg                : xG total (qualité des occasions)
        - xg_per_shot       : xG moyen par tir (qualité de sélection)
        - conversion_rate   : taux de conversion réel (buts / tirs) en %
        - xg_conversion     : taux de conversion attendu (xG / tirs) en %
        - overperformance   : buts - xG (positif = surperformant)
        - shots_on_target   : tirs cadrés (Goal + Saved)
        - on_target_rate    : % de tirs cadrés
        - big_chances       : occasions à xG ≥ 0.3
        - big_chances_scored: grandes occasions converties
        - headed_shots      : tirs de la tête
        - left_foot_shots   : tirs du pied gauche
        - right_foot_shots  : tirs du pied droit

    Exemple :
        >>> profile = player_shooting_profile(shots)
        >>> # Top 10 par xG total
        >>> print(profile.sort_values('xg', ascending=False).head(10))
        >>> # Les meilleurs surperformants
        >>> print(profile.sort_values('overperformance', ascending=False).head(10))
    """
    if df.empty:
        return pd.DataFrame()

    # --- Agrégation principale ---
    agg = df.groupby("player").agg(
        team=("team", lambda x: x.mode()[0]),   # équipe la plus fréquente (en cas de transfert)
        shots=("xg", "count"),
        goals=("is_goal", "sum"),
        xg=("xg", "sum"),
        xg_per_shot=("xg", "mean"),
    ).reset_index()

    # --- Métriques calculées ---
    agg["conversion_rate"] = (agg["goals"] / agg["shots"] * 100).round(1)
    agg["xg_conversion"]   = (agg["xg"] / agg["shots"] * 100).round(1)

    # Overperformance : différence buts réels vs attendus
    # Positif = marque plus que prévu → finisseur efficace (ou chanceux)
    # Négatif = marque moins que prévu → inefficace (ou malchanceux)
    agg["overperformance"] = (agg["goals"] - agg["xg"]).round(2)

    # --- Tirs cadrés (Goal ou Saved = cadré ; Off T, Blocked, Wayward = non cadré) ---
    on_target = df[df["outcome"].isin(["Goal", "Saved"])].groupby("player").size().rename("shots_on_target")
    agg = agg.merge(on_target, on="player", how="left")
    agg["shots_on_target"] = agg["shots_on_target"].fillna(0).astype(int)
    agg["on_target_rate"]  = (agg["shots_on_target"] / agg["shots"] * 100).round(1)

    # --- Big chances (xG ≥ 0.3) ---
    big = df[df["xg"] >= BIG_CHANCE_XG_THRESHOLD]
    big_total   = big.groupby("player").size().rename("big_chances")
    big_scored  = big[big["is_goal"]].groupby("player").size().rename("big_chances_scored")
    agg = agg.merge(big_total,  on="player", how="left")
    agg = agg.merge(big_scored, on="player", how="left")
    agg["big_chances"]        = agg["big_chances"].fillna(0).astype(int)
    agg["big_chances_scored"] = agg["big_chances_scored"].fillna(0).astype(int)

    # --- Répartition par partie du corps ---
    body_counts = df.groupby(["player", "body_part"]).size().unstack(fill_value=0)
    for col, alias in [("Head", "headed_shots"), ("Left Foot", "left_foot_shots"), ("Right Foot", "right_foot_shots")]:
        agg[alias] = agg["player"].map(body_counts.get(col, pd.Series(dtype=int))).fillna(0).astype(int)

    # --- Arrondi xG ---
    agg["xg"]         = agg["xg"].round(2)
    agg["xg_per_shot"] = agg["xg_per_shot"].round(3)

    return agg.sort_values("xg", ascending=False).reset_index(drop=True)


# ============================================================
# FONCTION 2 : Profil équipe — statistiques par équipe
# ============================================================

def team_shooting_profile(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcule le profil de tir pour chaque équipe.

    Utile pour comparer l'efficacité offensive des équipes :
    qui crée le plus d'occasions de qualité ? qui les convertit le mieux ?

    Args:
        df (pd.DataFrame) : DataFrame de tirs

    Returns:
        pd.DataFrame indexé par équipe avec :
        - shots             : tirs totaux
        - goals             : buts réels
        - xg                : xG total
        - xg_per_shot       : qualité moyenne des occasions
        - overperformance   : buts - xG
        - conversion_rate   : % de conversion réelle
        - big_chances       : occasions à xG ≥ 0.3
        - shots_on_target   : tirs cadrés
        - on_target_rate    : % cadrés
        - xg_per_match      : xG moyen par match (intensité offensive)

    Exemple :
        >>> teams = team_shooting_profile(shots)
        >>> print(teams.sort_values('xg_per_match', ascending=False))
    """
    if df.empty:
        return pd.DataFrame()

    n_matches_per_team = df.groupby("team")["match_id"].nunique().rename("matches_played")

    agg = df.groupby("team").agg(
        shots=("xg", "count"),
        goals=("is_goal", "sum"),
        xg=("xg", "sum"),
        xg_per_shot=("xg", "mean"),
    ).reset_index()

    agg["overperformance"] = (agg["goals"] - agg["xg"]).round(2)
    agg["conversion_rate"] = (agg["goals"] / agg["shots"] * 100).round(1)
    agg["xg"]              = agg["xg"].round(2)
    agg["xg_per_shot"]     = agg["xg_per_shot"].round(3)

    on_target = df[df["outcome"].isin(["Goal", "Saved"])].groupby("team").size().rename("shots_on_target")
    agg = agg.merge(on_target, on="team", how="left")
    agg["shots_on_target"] = agg["shots_on_target"].fillna(0).astype(int)
    agg["on_target_rate"]  = (agg["shots_on_target"] / agg["shots"] * 100).round(1)

    big = df[df["xg"] >= BIG_CHANCE_XG_THRESHOLD].groupby("team").size().rename("big_chances")
    agg = agg.merge(big, on="team", how="left")
    agg["big_chances"] = agg["big_chances"].fillna(0).astype(int)

    agg = agg.merge(n_matches_per_team, on="team", how="left")
    agg["xg_per_match"] = (agg["xg"] / agg["matches_played"]).round(2)

    return agg.sort_values("xg", ascending=False).reset_index(drop=True)


# ============================================================
# FONCTION 3 : xG par zone du terrain
# ============================================================

def xg_by_zone(df: pd.DataFrame) -> pd.DataFrame:
    """
    Découpe le terrain en zones et calcule les stats xG pour chacune.

    Zones définies (terrain de 120 x 80) :
    ┌──────────────────────────────────────────────┐
    │                                              │
    │  Zone 6: Gauche lointain  │  Zone 5: Central lointain  │  Zone 4: Droit lointain  │
    │  (x 80-100, y 0-27)      │  (x 80-100, y 27-53)       │  (x 80-100, y 53-80)     │
    │──────────────────────────────────────────────│
    │  Zone 3: Gauche proche   │  Zone 2: Surface centrale  │  Zone 1: Droit proche    │
    │  (x 100-120, y 0-27)     │  (x 100-120, y 27-53)      │  (x 100-120, y 53-80)    │
    │                          │  ← Zone la plus dangereuse │                          │
    └──────────────────────────────────────────────┘
    + Zone 7 : Hors surface (x < 80)
    + Zone 8 : Penalty (xG ≥ 0.7)

    Args:
        df (pd.DataFrame) : DataFrame de tirs

    Returns:
        pd.DataFrame avec pour chaque zone :
        - zone_name     : nom lisible de la zone
        - shots         : nombre de tirs
        - goals         : buts
        - xg_total      : xG total
        - xg_mean       : xG moyen par tir (qualité)
        - conversion    : % de conversion

    Exemple :
        >>> zones = xg_by_zone(shots)
        >>> print(zones.sort_values('xg_mean', ascending=False))
    """
    if df.empty or "x" not in df.columns:
        return pd.DataFrame()

    df = df.copy()

    def classify_zone(row):
        x = row["x"]
        y = row["y"]
        if pd.isna(x) or pd.isna(y):
            return "Inconnu"
        if x < 80:
            return "Hors surface lointaine"
        if row["xg"] >= 0.7:
            return "Penalty / but vide"
        if x >= 100:
            if 27 <= y <= 53:
                return "Surface centrale (6 yards)"
            elif y < 27:
                return "Surface gauche"
            else:
                return "Surface droite"
        else:  # x entre 80 et 100
            if 27 <= y <= 53:
                return "Entrée de surface centrale"
            elif y < 27:
                return "Entrée de surface gauche"
            else:
                return "Entrée de surface droite"

    df["zone"] = df.apply(classify_zone, axis=1)

    zones = df.groupby("zone").agg(
        shots=("xg", "count"),
        goals=("is_goal", "sum"),
        xg_total=("xg", "sum"),
        xg_mean=("xg", "mean"),
    ).reset_index()

    zones["conversion"] = (zones["goals"] / zones["shots"] * 100).round(1)
    zones["xg_total"]   = zones["xg_total"].round(2)
    zones["xg_mean"]    = zones["xg_mean"].round(3)
    zones = zones.rename(columns={"zone": "zone_name"})

    return zones.sort_values("xg_mean", ascending=False).reset_index(drop=True)


# ============================================================
# FONCTION 4 : Distribution xG — profil de qualité des tirs
# ============================================================

def xg_distribution(df: pd.DataFrame, bins: int = 10) -> pd.DataFrame:
    """
    Répartit les tirs en tranches de xG pour analyser la qualité des occasions.

    Permet de répondre à : "Est-ce que cette équipe/joueur crée beaucoup
    de petites occasions ou peu de très grosses occasions ?"

    Args:
        df (pd.DataFrame) : DataFrame de tirs
        bins (int)         : nombre de tranches (défaut : 10, soit 0-0.1, 0.1-0.2...)

    Returns:
        pd.DataFrame avec pour chaque tranche :
        - xg_range      : label de la tranche (ex: "0.10–0.20")
        - shots         : nombre de tirs dans cette tranche
        - goals         : buts dans cette tranche
        - xg_total      : xG total
        - conversion    : % de conversion

    Exemple :
        >>> dist = xg_distribution(shots_messi)
        >>> # Voir si Messi tire beaucoup ou peu, et à quel xG
    """
    if df.empty:
        return pd.DataFrame()

    edges = np.linspace(0, 1, bins + 1)
    labels = [f"{edges[i]:.2f}–{edges[i+1]:.2f}" for i in range(bins)]

    df = df.copy()
    df["xg_bin"] = pd.cut(df["xg"], bins=edges, labels=labels, include_lowest=True)

    dist = df.groupby("xg_bin", observed=True).agg(
        shots=("xg", "count"),
        goals=("is_goal", "sum"),
        xg_total=("xg", "sum"),
    ).reset_index()

    dist["conversion"] = (dist["goals"] / dist["shots"].replace(0, np.nan) * 100).round(1)
    dist["xg_total"]   = dist["xg_total"].round(2)
    dist = dist.rename(columns={"xg_bin": "xg_range"})

    return dist


# ============================================================
# FONCTION 5 : Analyse temporelle — xG par tranche de match
# ============================================================

def xg_by_time_period(df: pd.DataFrame, period_length: int = 15) -> pd.DataFrame:
    """
    Découpe le match en tranches de temps et calcule le xG pour chacune.

    Utile pour savoir à quel moment du match les équipes sont les plus
    dangereuses (montée en pression en fin de match ? départ canon ?)

    Args:
        df (pd.DataFrame)   : DataFrame de tirs
        period_length (int) : durée de chaque tranche en minutes (défaut : 15)

    Returns:
        pd.DataFrame avec :
        - period            : label de la tranche (ex: "30–45")
        - shots             : nombre de tirs
        - goals             : buts
        - xg_total          : xG total
        - xg_per_shot       : xG moyen par tir

    Exemple :
        >>> tempo = xg_by_time_period(shots)
        >>> # Voir si l'équipe est plus dangereuse en fin de match
    """
    if df.empty:
        return pd.DataFrame()

    df = df.copy()
    max_minute = max(df["minute"].max(), 90)
    edges  = list(range(0, max_minute + period_length, period_length))
    labels = [f"{edges[i]}–{edges[i+1]}" for i in range(len(edges) - 1)]

    df["period"] = pd.cut(df["minute"], bins=edges, labels=labels, include_lowest=True)

    tempo = df.groupby("period", observed=True).agg(
        shots=("xg", "count"),
        goals=("is_goal", "sum"),
        xg_total=("xg", "sum"),
        xg_per_shot=("xg", "mean"),
    ).reset_index()

    tempo["xg_total"]    = tempo["xg_total"].round(2)
    tempo["xg_per_shot"] = tempo["xg_per_shot"].round(3)

    return tempo


# ============================================================
# FONCTION 6 : Classement global — top tireurs
# ============================================================

def top_shooters(
    df: pd.DataFrame,
    metric: str = "xg",
    top_n: int = 15,
    min_shots: int = MIN_SHOTS_FOR_RANKING
) -> pd.DataFrame:
    """
    Retourne le classement des meilleurs tireurs selon une métrique donnée.

    Args:
        df (pd.DataFrame) : DataFrame de tirs
        metric (str)      : colonne sur laquelle classer.
                            Options : 'xg', 'goals', 'overperformance',
                                      'xg_per_shot', 'on_target_rate', 'big_chances'
        top_n (int)       : nombre de joueurs à retourner
        min_shots (int)   : nombre minimum de tirs pour être inclus

    Returns:
        pd.DataFrame des top N joueurs avec leur profil complet

    Exemple :
        >>> # Top 10 par xG total
        >>> print(top_shooters(shots, metric='xg', top_n=10))
        >>> # Top finisseurs (overperformance)
        >>> print(top_shooters(shots, metric='overperformance', top_n=10))
        >>> # Meilleurs sélecteurs de tir (xG/tir)
        >>> print(top_shooters(shots, metric='xg_per_shot', top_n=10, min_shots=10))
    """
    profile = player_shooting_profile(df)

    if profile.empty:
        return pd.DataFrame()

    # Filtrage par nombre minimum de tirs
    profile = profile[profile["shots"] >= min_shots]

    if metric not in profile.columns:
        raise ValueError(f"Métrique '{metric}' inconnue. Options : {profile.columns.tolist()}")

    return profile.sort_values(metric, ascending=False).head(top_n).reset_index(drop=True)


# ============================================================
# FONCTION 7 : Comparaison deux joueurs
# ============================================================

def compare_players(df: pd.DataFrame, player1: str, player2: str) -> pd.DataFrame:
    """
    Génère un tableau comparatif entre deux joueurs.

    Args:
        df (pd.DataFrame) : DataFrame de tirs
        player1 (str)     : nom (ou fragment) du joueur 1
        player2 (str)     : nom (ou fragment) du joueur 2

    Returns:
        pd.DataFrame de comparaison (métriques en lignes, joueurs en colonnes)

    Exemple :
        >>> comp = compare_players(shots, "Messi", "Benzema")
        >>> print(comp)
    """
    profile = player_shooting_profile(df)

    p1 = profile[profile["player"].str.contains(player1, case=False, na=False)]
    p2 = profile[profile["player"].str.contains(player2, case=False, na=False)]

    if p1.empty or p2.empty:
        missing = player1 if p1.empty else player2
        raise ValueError(f"Joueur '{missing}' non trouvé. Vérifie l'orthographe.")

    # On prend la première correspondance si plusieurs résultats
    p1 = p1.iloc[0]
    p2 = p2.iloc[0]

    metrics = [
        "shots", "goals", "xg", "xg_per_shot",
        "conversion_rate", "overperformance",
        "shots_on_target", "on_target_rate",
        "big_chances", "big_chances_scored",
        "headed_shots", "left_foot_shots", "right_foot_shots"
    ]

    comparison = pd.DataFrame({
        "métrique":   metrics,
        p1["player"]: [p1[m] for m in metrics],
        p2["player"]: [p2[m] for m in metrics],
    })

    return comparison


# ============================================================
# TEST RAPIDE
# ============================================================

if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    from src.data_loader import load_matches, load_shots_from_match

    print("🔍 Test de metrics.py...\n")

    # Chargement d'un match test
    matches = load_matches(competition_id=11, season_id=90)
    match_id = matches.iloc[0]["match_id"]
    shots = load_shots_from_match(match_id)

    print(f"✅ {len(shots)} tirs chargés\n")

    # Test profil joueur
    print("👤 Profil joueurs :")
    profile = player_shooting_profile(shots)
    print(profile[["player", "shots", "goals", "xg", "overperformance", "on_target_rate"]].head(8).to_string(index=False))

    # Test profil équipe
    print("\n🏟️ Profil équipes :")
    teams = team_shooting_profile(shots)
    print(teams[["team", "shots", "goals", "xg", "overperformance", "xg_per_shot"]].to_string(index=False))

    # Test zones
    print("\n🗺️ xG par zone :")
    zones = xg_by_zone(shots)
    print(zones.to_string(index=False))

    # Test distribution
    print("\n📊 Distribution xG :")
    dist = xg_distribution(shots)
    print(dist[dist["shots"] > 0].to_string(index=False))
