"""
data_loader.py — Chargement et nettoyage des données de tirs StatsBomb
=======================================================================

Ce module est la FONDATION du projet xG & Shooting Profile Analysis.
Il fait une seule chose, mais bien : récupérer les données StatsBomb
et les transformer en un DataFrame propre et prêt à analyser.

Pourquoi StatsBomb ?
--------------------
StatsBomb met à disposition des données open source GRATUITES sur :
- La Liga (plusieurs saisons)
- Champions League (plusieurs saisons)
- WSL (Women's Super League)
- Euro, Coupe du Monde féminine, etc.

Ces données incluent des métriques avancées comme le xG (expected goals),
qui ne sont pas disponibles dans la plupart des sources gratuites.

Workflow de ce module :
    1. Lister les compétitions disponibles
    2. Récupérer les matchs d'une compétition/saison
    3. Charger les événements de tous les matchs
    4. Filtrer uniquement les tirs (type == "Shot")
    5. Nettoyer et enrichir les données
    6. Retourner un DataFrame prêt à l'emploi
"""

import warnings
import pandas as pd
from pathlib import Path
from statsbombpy import sb

# On supprime le warning "no credentials" — normal pour les open data
warnings.filterwarnings("ignore")

# ============================================================
# CONSTANTES — Compétitions disponibles en open data
# ============================================================
# Ces IDs sont fixes chez StatsBomb.
# Tu peux en trouver d'autres avec : sb.competitions()

COMPETITIONS = {
    "La Liga 2020/2021":         {"competition_id": 11,  "season_id": 90},
    "La Liga 2019/2020":         {"competition_id": 11,  "season_id": 42},
    "Champions League 2018/2019":{"competition_id": 16,  "season_id": 4},
    "Champions League 2017/2018":{"competition_id": 16,  "season_id": 1},
    "WSL 2020/2021":             {"competition_id": 37,  "season_id": 90},
    "EURO 2020":                 {"competition_id": 55,  "season_id": 43},
    "Coupe du Monde 2022":       {"competition_id": 43,  "season_id": 106},
}

# Dossier de cache (évite de re-télécharger à chaque exécution)
CACHE_DIR = Path("data/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# FONCTION 1 : Lister les compétitions disponibles
# ============================================================

def list_competitions() -> pd.DataFrame:
    """
    Retourne la liste de toutes les compétitions StatsBomb open data.

    Utile pour explorer ce qui est disponible avant de charger des matchs.

    Returns:
        pd.DataFrame avec les colonnes :
        - competition_name  : nom de la compétition
        - season_name       : nom de la saison
        - competition_id    : ID à utiliser dans les autres fonctions
        - season_id         : ID de saison à utiliser

    Exemple :
        >>> comps = list_competitions()
        >>> print(comps[['competition_name', 'season_name']].to_string())
    """
    comps = sb.competitions()
    return comps[["competition_id", "season_id", "competition_name", "season_name"]].sort_values(
        ["competition_name", "season_name"]
    ).reset_index(drop=True)


# ============================================================
# FONCTION 2 : Charger les matchs d'une compétition
# ============================================================

def load_matches(competition_id: int, season_id: int) -> pd.DataFrame:
    """
    Retourne la liste des matchs pour une compétition et une saison données.

    Args:
        competition_id (int) : ID de la compétition (voir COMPETITIONS ou list_competitions())
        season_id (int)      : ID de la saison

    Returns:
        pd.DataFrame avec notamment :
        - match_id      : ID unique du match (nécessaire pour charger les événements)
        - home_team     : équipe à domicile
        - away_team     : équipe à l'extérieur
        - home_score    : score domicile
        - away_score    : score extérieur
        - match_date    : date du match

    Exemple :
        >>> matches = load_matches(competition_id=11, season_id=90)
        >>> print(matches[['home_team', 'away_team', 'match_date']].head())
    """
    matches = sb.matches(competition_id=competition_id, season_id=season_id)
    return matches[["match_id", "match_date", "home_team", "away_team",
                    "home_score", "away_score", "competition_name"]].sort_values("match_date")


# ============================================================
# FONCTION 3 : Charger et nettoyer les tirs d'UN match
# ============================================================

def load_shots_from_match(match_id: int) -> pd.DataFrame:
    """
    Charge tous les tirs d'un match spécifique et retourne un DataFrame propre.

    Cette fonction :
    1. Télécharge TOUS les événements du match (passes, dribbles, tirs, etc.)
    2. Filtre uniquement les événements de type "Shot"
    3. Extrait les colonnes utiles et renomme proprement
    4. Sépare les coordonnées [x, y] en deux colonnes distinctes

    Args:
        match_id (int) : ID du match (obtenu via load_matches())

    Returns:
        pd.DataFrame avec les colonnes :
        - player        : nom du joueur tireur
        - team          : équipe du joueur
        - minute        : minute du tir
        - xg            : valeur xG du tir (0 à 1 — probabilité de but)
        - outcome       : résultat du tir (Goal, Saved, Off T, Blocked, Wayward)
        - is_goal       : booléen — True si c'est un but
        - body_part     : partie du corps (Right Foot, Left Foot, Head)
        - technique     : technique (Normal, Volley, Half Volley, Lob...)
        - shot_type     : contexte (Open Play, Free Kick, Corner, Penalty)
        - under_pressure: booléen — True si le joueur était sous pression
        - first_time    : booléen — True si tir du premier contact
        - open_goal     : booléen — True si but vide
        - x, y          : coordonnées du tir sur le terrain (pitch 120x80)
        - match_id      : ID du match (pour jointures ultérieures)

    Note sur les coordonnées :
        StatsBomb utilise un terrain de 120 x 80 unités.
        x=0 = ligne de but défensive, x=120 = ligne de but adverse
        y=0 = côté gauche, y=80 = côté droit (vu de derrière)

    Exemple :
        >>> shots = load_shots_from_match(match_id=3773386)
        >>> print(shots[['player', 'xg', 'outcome']].head())
    """
    # Téléchargement de TOUS les événements du match
    events = sb.events(match_id=match_id)

    # Filtrage : on ne garde que les tirs
    shots_raw = events[events["type"] == "Shot"].copy()

    if shots_raw.empty:
        return pd.DataFrame()

    # --- Extraction des coordonnées x, y ---
    # La colonne "location" contient une liste [x, y]
    # On la sépare en deux colonnes distinctes pour pouvoir tracer sur le terrain
    shots_raw["x"] = shots_raw["location"].apply(lambda loc: loc[0] if isinstance(loc, list) else None)
    shots_raw["y"] = shots_raw["location"].apply(lambda loc: loc[1] if isinstance(loc, list) else None)

    # --- Sélection et renommage des colonnes utiles ---
    shots_clean = pd.DataFrame({
        "match_id":       match_id,
        "player":         shots_raw["player"],
        "team":           shots_raw["team"],
        "minute":         shots_raw["minute"],
        "xg":             shots_raw["shot_statsbomb_xg"],
        "outcome":        shots_raw["shot_outcome"],
        "body_part":      shots_raw["shot_body_part"],
        "technique":      shots_raw["shot_technique"],
        "shot_type":      shots_raw["shot_type"],
        # Certaines colonnes n'existent pas dans tous les matchs → .get() avec valeur par défaut
        "under_pressure": shots_raw.get("under_pressure",     pd.Series(False, index=shots_raw.index)).fillna(False),
        "first_time":     shots_raw.get("shot_first_time",    pd.Series(False, index=shots_raw.index)).fillna(False),
        "open_goal":      shots_raw.get("shot_open_goal",     pd.Series(False, index=shots_raw.index)).fillna(False),
        "x":              shots_raw["x"],
        "y":              shots_raw["y"],
    })

    # --- Colonne calculée : is_goal ---
    # Plus pratique qu'un string "Goal" pour les calculs (somme, moyenne, etc.)
    shots_clean["is_goal"] = shots_clean["outcome"] == "Goal"

    return shots_clean.reset_index(drop=True)


# ============================================================
# FONCTION 4 : Charger TOUS les tirs d'une compétition entière
# ============================================================

def load_shots_from_competition(
    competition_id: int,
    season_id: int,
    use_cache: bool = True,
    verbose: bool = True
) -> pd.DataFrame:
    """
    Charge et agrège les tirs de TOUS les matchs d'une compétition/saison.

    C'est la fonction principale que tu utiliseras pour les analyses.
    Elle appelle load_shots_from_match() sur chaque match et assemble le tout.

    Un système de cache est intégré : les données sont sauvegardées en CSV
    pour éviter de re-télécharger à chaque exécution (peut prendre quelques
    minutes selon le nombre de matchs).

    Args:
        competition_id (int) : ID de la compétition
        season_id (int)      : ID de la saison
        use_cache (bool)     : True = utilise le cache si disponible (recommandé)
        verbose (bool)       : True = affiche la progression match par match

    Returns:
        pd.DataFrame avec tous les tirs de la compétition,
        mêmes colonnes que load_shots_from_match() + colonnes enrichies.

    Exemple :
        >>> shots = load_shots_from_competition(competition_id=11, season_id=90)
        >>> print(f"{len(shots)} tirs chargés")
        >>> print(shots.groupby('team')['is_goal'].sum().sort_values(ascending=False))
    """
    cache_file = CACHE_DIR / f"shots_{competition_id}_{season_id}.csv"

    # --- Vérification du cache ---
    if use_cache and cache_file.exists():
        if verbose:
            print(f"📂 Cache trouvé — chargement depuis {cache_file}")
        return pd.read_csv(cache_file)

    # --- Chargement des matchs ---
    if verbose:
        print(f"🌐 Récupération des matchs (competition={competition_id}, season={season_id})...")

    matches = load_matches(competition_id=competition_id, season_id=season_id)

    if verbose:
        print(f"📋 {len(matches)} matchs trouvés — téléchargement des tirs en cours...\n")

    # --- Chargement des tirs match par match ---
    all_shots = []

    for i, row in matches.iterrows():
        match_id   = row["match_id"]
        home_team  = row["home_team"]
        away_team  = row["away_team"]
        match_date = row["match_date"]

        if verbose:
            print(f"  [{i+1}/{len(matches)}] {match_date} — {home_team} vs {away_team}...")

        shots = load_shots_from_match(match_id)

        if not shots.empty:
            # On enrichit avec les infos du match
            shots["home_team"]  = home_team
            shots["away_team"]  = away_team
            shots["match_date"] = match_date
            all_shots.append(shots)

    # --- Assemblage final ---
    if not all_shots:
        print("⚠️ Aucun tir trouvé.")
        return pd.DataFrame()

    df = pd.concat(all_shots, ignore_index=True)

    # --- Sauvegarde en cache ---
    df.to_csv(cache_file, index=False)

    if verbose:
        print(f"\n✅ {len(df)} tirs chargés et sauvegardés dans {cache_file}")

    return df


# ============================================================
# FONCTION 5 : Filtrer par équipe ou joueur
# ============================================================

def filter_shots(
    df: pd.DataFrame,
    team: str = None,
    player: str = None,
    outcome: str = None,
    body_part: str = None,
    min_xg: float = None,
) -> pd.DataFrame:
    """
    Applique des filtres sur un DataFrame de tirs.

    Toutes les options sont facultatives — tu peux en combiner plusieurs.

    Args:
        df (pd.DataFrame)  : DataFrame de tirs (issu de load_shots_from_competition)
        team (str)         : filtre sur l'équipe (ex: "Barcelona")
        player (str)       : filtre sur le joueur (ex: "Lionel Messi")
        outcome (str)      : filtre sur le résultat (ex: "Goal", "Saved", "Off T")
        body_part (str)    : filtre sur la partie du corps (ex: "Right Foot", "Head")
        min_xg (float)     : filtre sur xG minimum (ex: 0.3 pour les grosses occasions)

    Returns:
        pd.DataFrame filtré

    Exemple :
        >>> # Tous les tirs de Messi hors penaltys
        >>> messi_shots = filter_shots(shots, player="Lionel Messi")
        >>> barca_goals = filter_shots(shots, team="Barcelona", outcome="Goal")
        >>> big_chances = filter_shots(shots, min_xg=0.3)
    """
    filtered = df.copy()

    if team:
        # Recherche partielle insensible à la casse (ex: "barca" trouve "Barcelona")
        filtered = filtered[filtered["team"].str.contains(team, case=False, na=False)]

    if player:
        filtered = filtered[filtered["player"].str.contains(player, case=False, na=False)]

    if outcome:
        filtered = filtered[filtered["outcome"].str.contains(outcome, case=False, na=False)]

    if body_part:
        filtered = filtered[filtered["body_part"].str.contains(body_part, case=False, na=False)]

    if min_xg is not None:
        filtered = filtered[filtered["xg"] >= min_xg]

    return filtered.reset_index(drop=True)


# ============================================================
# FONCTION 6 : Stats rapides de validation
# ============================================================

def quick_summary(df: pd.DataFrame) -> None:
    """
    Affiche un résumé rapide du DataFrame de tirs.
    Utile pour valider que les données sont bien chargées.

    Args:
        df (pd.DataFrame) : DataFrame de tirs

    Exemple :
        >>> shots = load_shots_from_competition(11, 90)
        >>> quick_summary(shots)
    """
    if df.empty:
        print("⚠️ DataFrame vide.")
        return

    n_shots   = len(df)
    n_goals   = df["is_goal"].sum()
    total_xg  = df["xg"].sum()
    n_players = df["player"].nunique()
    n_teams   = df["team"].nunique()
    n_matches = df["match_id"].nunique()

    print("=" * 45)
    print("📊 RÉSUMÉ DES DONNÉES")
    print("=" * 45)
    print(f"  Matchs analysés   : {n_matches}")
    print(f"  Équipes           : {n_teams}")
    print(f"  Joueurs tireurs   : {n_players}")
    print(f"  Tirs totaux       : {n_shots}")
    print(f"  Buts réels        : {n_goals}")
    print(f"  xG total          : {total_xg:.1f}")
    print(f"  Conversion réelle : {n_goals/n_shots*100:.1f}%")
    print(f"  Conversion xG     : {n_goals/total_xg:.2f} (1.0 = normal)")
    print("=" * 45)
    print("\n  Répartition par résultat :")
    print(df["outcome"].value_counts().to_string())
    print("\n  Répartition par partie du corps :")
    print(df["body_part"].value_counts().to_string())
    print("=" * 45)


# ============================================================
# TEST RAPIDE — exécute ce fichier directement pour vérifier
# ============================================================

if __name__ == "__main__":
    print("🔍 Test du data_loader...\n")

    # 1. Liste des compétitions
    print("📋 Compétitions disponibles (extrait) :")
    comps = list_competitions()
    print(comps.head(8).to_string(index=False))

    # 2. Chargement d'UN match (rapide)
    print("\n\n⚽ Chargement des tirs d'un match test (La Liga)...")
    test_matches = load_matches(competition_id=11, season_id=90)
    test_match_id = test_matches.iloc[0]["match_id"]
    shots_test = load_shots_from_match(test_match_id)
    print(f"✅ {len(shots_test)} tirs chargés pour le match {test_match_id}")
    print(shots_test[["player", "team", "xg", "outcome", "body_part"]].head(5).to_string(index=False))

    # 3. Résumé
    print("\n")
    quick_summary(shots_test)
