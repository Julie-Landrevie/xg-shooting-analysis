"""
viz.py — Visualisations xG & Shooting Profile Analysis
=======================================================

Ce module crée toutes les visualisations du projet.
Chaque fonction prend un DataFrame de tirs ou de métriques,
et retourne une figure matplotlib prête à afficher ou sauvegarder.

Visualisations disponibles :
  1. shot_map()               — carte des tirs sur le terrain (xG = taille des points)
  2. player_xg_bar()          — barres xG vs buts réels par joueur
  3. overperformance_chart()  — lollipop chart buts - xG
  4. xg_distribution_plot()   — histogramme de qualité des occasions
  5. xg_by_zone_heatmap()     — heatmap des zones de tir sur le terrain
  6. xg_timeline()            — évolution du xG au fil du match
  7. shooting_profile_radar()  — radar chart profil tireur

Palette de couleurs :
  On utilise une charte graphique cohérente sur toutes les vues.
  Fond sombre (#1a1a2e), accents bleu/violet (#4e9af1/#a855f7),
  buts en or (#f59e0b), non-buts en gris (#475569).
"""

import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")   # Backend non-interactif (compatible Streamlit et notebooks)
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
from matplotlib.colors import LinearSegmentedColormap
from mplsoccer import Pitch, VerticalPitch

warnings.filterwarnings("ignore")

# ============================================================
# CHARTE GRAPHIQUE — couleurs et styles
# ============================================================

COLORS = {
    "background":  "#1a1a2e",   # Fond principal (bleu nuit)
    "panel":       "#16213e",   # Fond secondaire (panneaux)
    "accent_blue": "#4e9af1",   # Couleur principale (xG, tirs)
    "accent_purple":"#a855f7",  # Couleur secondaire (tendances)
    "goal":        "#f59e0b",   # Buts (or)
    "no_goal":     "#475569",   # Non-buts (gris ardoise)
    "text":        "#e2e8f0",   # Texte principal
    "text_muted":  "#94a3b8",   # Texte secondaire
    "grid":        "#2d3748",   # Grilles et séparateurs
    "positive":    "#10b981",   # Overperformance positive (vert)
    "negative":    "#ef4444",   # Overperformance négative (rouge)
}

# Style global matplotlib
plt.rcParams.update({
    "figure.facecolor":  COLORS["background"],
    "axes.facecolor":    COLORS["panel"],
    "axes.edgecolor":    COLORS["grid"],
    "axes.labelcolor":   COLORS["text"],
    "axes.titlecolor":   COLORS["text"],
    "xtick.color":       COLORS["text_muted"],
    "ytick.color":       COLORS["text_muted"],
    "text.color":        COLORS["text"],
    "grid.color":        COLORS["grid"],
    "grid.linestyle":    "--",
    "grid.alpha":        0.5,
    "font.family":       "DejaVu Sans",
})

def _fig_title(fig, title: str, subtitle: str = "") -> None:
    """Ajoute un titre principal et un sous-titre à une figure."""
    fig.text(0.5, 0.97, title, ha="center", va="top",
             fontsize=16, fontweight="bold", color=COLORS["text"])
    if subtitle:
        fig.text(0.5, 0.93, subtitle, ha="center", va="top",
                 fontsize=10, color=COLORS["text_muted"])

def _watermark(fig) -> None:
    """Ajoute la signature en bas de figure."""
    fig.text(0.99, 0.01, "Julie Landrevie — xG Analysis | StatsBomb Open Data",
             ha="right", va="bottom", fontsize=7, color=COLORS["text_muted"], style="italic")


# ============================================================
# VIZ 1 : Shot Map — carte des tirs sur le terrain
# ============================================================

def shot_map(
    df: pd.DataFrame,
    title: str = "Shot Map",
    team: str = None,
    show_goals_only: bool = False,
) -> plt.Figure:
    """
    Affiche tous les tirs positionnés sur le terrain.

    Encodage visuel :
    - Position du point  = position du tir (x, y)
    - Taille du point    = valeur xG (plus gros = plus dangereux)
    - Couleur JAUNE/or   = but marqué
    - Couleur GRIS       = tir non converti
    - Contour blanc      = tir cadré (Saved ou Goal)

    La moitié du terrain est utilisée (vue offensive) car tous les tirs
    sont en zone offensive (x > 60 sur un terrain de 120 unités).

    Args:
        df (pd.DataFrame)      : DataFrame de tirs
        title (str)            : titre de la figure
        team (str)             : si renseigné, filtre sur cette équipe
        show_goals_only (bool) : si True, n'affiche que les buts

    Returns:
        matplotlib.figure.Figure

    Exemple :
        >>> fig = shot_map(shots, title="Barcelona — Shot Map La Liga 2020/21")
        >>> fig.savefig("shotmap.png", dpi=150, bbox_inches="tight")
    """
    if team:
        df = df[df["team"].str.contains(team, case=False, na=False)]
    if show_goals_only:
        df = df[df["is_goal"]]

    # Terrain vertical (attaque vers le haut) — demi-terrain
    pitch = VerticalPitch(
        pitch_type="statsbomb",
        half=True,
        pitch_color=COLORS["panel"],
        line_color="#5a6a7a",
        linewidth=1.2,
    )

    fig, ax = pitch.draw(figsize=(8, 7))
    fig.patch.set_facecolor(COLORS["background"])

    if df.empty:
        ax.text(40, 80, "Aucun tir", ha="center", va="center",
                fontsize=14, color=COLORS["text_muted"])
        return fig

    # Taille des points proportionnelle au xG (min 50, max 600)
    sizes = (df["xg"] * 1000).clip(lower=50, upper=700)

    # Couleur : or si but, gris si non
    colors = df["is_goal"].map({True: COLORS["goal"], False: COLORS["no_goal"]})

    # Contour blanc si tir cadré
    edge_colors = df["outcome"].map(
        lambda o: "white" if o in ["Goal", "Saved"] else COLORS["panel"]
    )

    # Scatter plot des tirs
    # Note : VerticalPitch inverse les axes — on passe y en x et x en y
    sc = pitch.scatter(
        df["x"], df["y"],
        s=sizes,
        c=colors,
        edgecolors=edge_colors,
        linewidths=0.8,
        alpha=0.85,
        zorder=3,
        ax=ax,
    )

    # Légende manuelle
    legend_elements = [
        mpatches.Patch(facecolor=COLORS["goal"],    label=f"But ({df['is_goal'].sum()})"),
        mpatches.Patch(facecolor=COLORS["no_goal"], label=f"Non converti ({(~df['is_goal']).sum()})"),
        mpatches.Patch(facecolor="none", edgecolor="white", linewidth=1.2,
                       label="Cadré (Goal ou Saved)"),
    ]
    ax.legend(handles=legend_elements, loc="lower center",
              bbox_to_anchor=(0.5, -0.04), ncol=3,
              facecolor=COLORS["panel"], edgecolor=COLORS["grid"],
              labelcolor=COLORS["text"], fontsize=8)

    # Stat summary en haut
    xg_total = df["xg"].sum()
    n_goals  = df["is_goal"].sum()
    n_shots  = len(df)
    ax.text(40, 122, f"{n_shots} tirs  |  {xg_total:.2f} xG  |  {n_goals} buts",
            ha="center", va="bottom", fontsize=9,
            color=COLORS["text_muted"],
            path_effects=[pe.withStroke(linewidth=2, foreground=COLORS["background"])])

    _fig_title(fig, title)
    _watermark(fig)
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    return fig


# ============================================================
# VIZ 2 : xG vs Buts — barres comparatives par joueur
# ============================================================

def player_xg_bar(
    df_metrics: pd.DataFrame,
    top_n: int = 12,
    metric: str = "xg",
    title: str = "xG vs Buts par joueur",
) -> plt.Figure:
    """
    Barres horizontales comparant xG attendu et buts réels par joueur.

    Deux barres côte à côte par joueur :
    - Barre bleue  = xG total (occasions créées)
    - Barre or     = buts réels

    Si buts > barre bleue → surperformant (barre or dépasse)
    Si buts < barre bleue → sous-performant (barre or plus courte)

    Args:
        df_metrics (pd.DataFrame) : sortie de player_shooting_profile()
        top_n (int)               : nombre de joueurs à afficher
        metric (str)              : métrique de tri ('xg', 'goals', 'shots')
        title (str)               : titre de la figure

    Returns:
        matplotlib.figure.Figure

    Exemple :
        >>> from src.metrics import player_shooting_profile
        >>> profile = player_shooting_profile(shots)
        >>> fig = player_xg_bar(profile, top_n=10, title="La Liga 2020/21")
    """
    data = df_metrics.sort_values(metric, ascending=False).head(top_n).copy()
    data = data.iloc[::-1]  # Inversion pour que le top soit en haut

    # Noms courts (prénom + nom, max 20 chars)
    data["short_name"] = data["player"].apply(
        lambda n: " ".join(n.split()[-2:]) if len(n) > 20 else n
    )

    fig, ax = plt.subplots(figsize=(10, top_n * 0.6 + 1.5))
    fig.patch.set_facecolor(COLORS["background"])
    ax.set_facecolor(COLORS["panel"])

    y = np.arange(len(data))
    h = 0.35  # hauteur des barres

    bars_xg   = ax.barh(y + h/2, data["xg"],    height=h, color=COLORS["accent_blue"],  alpha=0.85, label="xG")
    bars_goal = ax.barh(y - h/2, data["goals"],  height=h, color=COLORS["goal"],         alpha=0.85, label="Buts réels")

    # Valeurs sur les barres
    for bar in bars_xg:
        w = bar.get_width()
        if w > 0.1:
            ax.text(w + 0.05, bar.get_y() + bar.get_height()/2,
                    f"{w:.1f}", va="center", ha="left", fontsize=7.5, color=COLORS["text"])

    for bar in bars_goal:
        w = bar.get_width()
        if w > 0:
            ax.text(w + 0.05, bar.get_y() + bar.get_height()/2,
                    f"{int(w)}", va="center", ha="left", fontsize=7.5, color=COLORS["text"])

    ax.set_yticks(y)
    ax.set_yticklabels(data["short_name"], fontsize=9)
    ax.set_xlabel("Valeur", color=COLORS["text_muted"])
    ax.legend(facecolor=COLORS["panel"], edgecolor=COLORS["grid"],
              labelcolor=COLORS["text"], fontsize=9)
    ax.grid(axis="x", alpha=0.3)
    ax.spines[["top", "right", "left"]].set_visible(False)

    _fig_title(fig, title, subtitle=f"Top {top_n} joueurs — xG (bleu) vs Buts réels (or)")
    _watermark(fig)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    return fig


# ============================================================
# VIZ 3 : Overperformance — lollipop chart
# ============================================================

def overperformance_chart(
    df_metrics: pd.DataFrame,
    top_n: int = 15,
    title: str = "Overperformance xG (Buts − xG)",
) -> plt.Figure:
    """
    Lollipop chart de l'overperformance : buts réels − xG attendus.

    Points à droite de 0 = surperformants (finisseurs efficaces)
    Points à gauche de 0 = sous-performants (malchanceux ou inefficaces)

    Args:
        df_metrics (pd.DataFrame) : sortie de player_shooting_profile()
        top_n (int)               : nombre de joueurs à afficher
        title (str)               : titre

    Returns:
        matplotlib.figure.Figure
    """
    data = df_metrics.sort_values("overperformance", ascending=False).head(top_n).copy()
    data = data.iloc[::-1]

    data["short_name"] = data["player"].apply(
        lambda n: " ".join(n.split()[-2:]) if len(n) > 20 else n
    )

    fig, ax = plt.subplots(figsize=(9, top_n * 0.55 + 1.5))
    fig.patch.set_facecolor(COLORS["background"])
    ax.set_facecolor(COLORS["panel"])

    y = np.arange(len(data))
    colors = [COLORS["positive"] if v >= 0 else COLORS["negative"]
              for v in data["overperformance"]]

    # Ligne horizontale à 0
    ax.axvline(x=0, color=COLORS["text_muted"], linewidth=1.2, alpha=0.7)

    # Tiges (hlines)
    ax.hlines(y, xmin=0, xmax=data["overperformance"],
              colors=colors, linewidth=2.5, alpha=0.7)

    # Points (lollipop heads)
    ax.scatter(data["overperformance"], y, color=colors, s=80, zorder=5, alpha=0.95)

    # Valeurs
    for i, (val, yi) in enumerate(zip(data["overperformance"], y)):
        offset = 0.05 if val >= 0 else -0.05
        ha = "left" if val >= 0 else "right"
        ax.text(val + offset, yi, f"{val:+.2f}",
                va="center", ha=ha, fontsize=7.5, color=COLORS["text"])

    ax.set_yticks(y)
    ax.set_yticklabels(data["short_name"], fontsize=9)
    ax.set_xlabel("Buts − xG", color=COLORS["text_muted"])
    ax.grid(axis="x", alpha=0.2)
    ax.spines[["top", "right", "left"]].set_visible(False)

    legend_elements = [
        mpatches.Patch(facecolor=COLORS["positive"], label="Surperformant (Buts > xG)"),
        mpatches.Patch(facecolor=COLORS["negative"], label="Sous-performant (Buts < xG)"),
    ]
    ax.legend(handles=legend_elements, loc="lower right",
              facecolor=COLORS["panel"], edgecolor=COLORS["grid"],
              labelcolor=COLORS["text"], fontsize=8)

    _fig_title(fig, title)
    _watermark(fig)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    return fig


# ============================================================
# VIZ 4 : Distribution xG — histogramme qualité des occasions
# ============================================================

def xg_distribution_plot(
    df: pd.DataFrame,
    title: str = "Distribution des xG",
    player: str = None,
    team: str = None,
) -> plt.Figure:
    """
    Histogramme de la distribution des valeurs xG des tirs.

    Permet de comprendre le profil d'un joueur ou d'une équipe :
    - Beaucoup de petits xG = créateur mais peu efficace en zone
    - Pics de haut xG = attaquant de surface, positions idéales

    Args:
        df (pd.DataFrame) : DataFrame de tirs
        title (str)       : titre
        player (str)      : filtre joueur (optionnel)
        team (str)        : filtre équipe (optionnel)

    Returns:
        matplotlib.figure.Figure
    """
    if player:
        df = df[df["player"].str.contains(player, case=False, na=False)]
    if team:
        df = df[df["team"].str.contains(team, case=False, na=False)]

    fig, ax = plt.subplots(figsize=(9, 5))
    fig.patch.set_facecolor(COLORS["background"])
    ax.set_facecolor(COLORS["panel"])

    bins = np.linspace(0, 1, 21)  # 20 bins de 0.05 chacun

    # Tous les tirs en bleu
    ax.hist(df["xg"], bins=bins,
            color=COLORS["accent_blue"], alpha=0.6, label="Tous les tirs", edgecolor=COLORS["panel"])

    # Buts en or par-dessus
    goals = df[df["is_goal"]]
    ax.hist(goals["xg"], bins=bins,
            color=COLORS["goal"], alpha=0.85, label=f"Buts ({len(goals)})", edgecolor=COLORS["panel"])

    # Ligne xG moyen
    xg_mean = df["xg"].mean()
    ax.axvline(xg_mean, color=COLORS["accent_purple"], linestyle="--", linewidth=1.5,
               label=f"xG moyen = {xg_mean:.3f}")

    ax.set_xlabel("Valeur xG", color=COLORS["text_muted"])
    ax.set_ylabel("Nombre de tirs", color=COLORS["text_muted"])
    ax.legend(facecolor=COLORS["panel"], edgecolor=COLORS["grid"],
              labelcolor=COLORS["text"], fontsize=9)
    ax.grid(axis="y", alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)

    # Annotations stats
    xg_total = df["xg"].sum()
    n_shots  = len(df)
    n_goals  = len(goals)
    ax.text(0.98, 0.95,
            f"{n_shots} tirs  |  {xg_total:.1f} xG total  |  {n_goals} buts",
            transform=ax.transAxes, ha="right", va="top",
            fontsize=8.5, color=COLORS["text_muted"])

    _fig_title(fig, title, subtitle="Distribution de la qualité des occasions créées")
    _watermark(fig)
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    return fig


# ============================================================
# VIZ 5 : Heatmap xG par zone sur le terrain
# ============================================================

def xg_zone_heatmap(
    df: pd.DataFrame,
    title: str = "Heatmap xG par zone",
    team: str = None,
) -> plt.Figure:
    """
    Heatmap des tirs sur le terrain : densité colorée par xG cumulé.

    Plus une zone est chaude, plus les tirs qui en proviennent
    sont dangereux (xG élevé).

    Args:
        df (pd.DataFrame) : DataFrame de tirs (doit avoir colonnes x, y)
        title (str)       : titre
        team (str)        : filtre équipe (optionnel)

    Returns:
        matplotlib.figure.Figure
    """
    if team:
        df = df[df["team"].str.contains(team, case=False, na=False)]

    df = df.dropna(subset=["x", "y"])

    pitch = VerticalPitch(
        pitch_type="statsbomb",
        half=True,
        pitch_color=COLORS["panel"],
        line_color="#5a6a7a",
        linewidth=1.2,
    )

    fig, ax = pitch.draw(figsize=(8, 7))
    fig.patch.set_facecolor(COLORS["background"])

    if df.empty:
        return fig

    # Colormap personnalisée : transparent → bleu → or
    cmap = LinearSegmentedColormap.from_list(
        "xg_heat", ["#16213e", COLORS["accent_blue"], COLORS["goal"]]
    )

    # Kernel Density sur le terrain (pondéré par xG)
    bs = pitch.bin_statistic(
        df["x"], df["y"],
        values=df["xg"],
        statistic="sum",
        bins=(12, 8),
    )

    hm = pitch.heatmap(bs, ax=ax, cmap=cmap, edgecolors=COLORS["background"], linewidth=0.5)

    # Colorbar
    cbar = fig.colorbar(hm, ax=ax, orientation="horizontal",
                        pad=0.02, fraction=0.03, aspect=40)
    cbar.set_label("xG cumulé par zone", color=COLORS["text_muted"], fontsize=8)
    cbar.ax.tick_params(colors=COLORS["text_muted"], labelsize=7)

    # Superposer les tirs (petits points)
    pitch.scatter(
        df["x"], df["y"],
        s=20,
        c=[COLORS["goal"] if g else COLORS["no_goal"] for g in df["is_goal"]],
        alpha=0.5,
        zorder=4,
        ax=ax,
    )

    _fig_title(fig, title, subtitle="Zones d'accumulation xG — taille = xG cumulé")
    _watermark(fig)
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    return fig


# ============================================================
# VIZ 6 : Timeline xG — évolution au fil du match
# ============================================================

def xg_timeline(
    df: pd.DataFrame,
    home_team: str,
    away_team: str,
    title: str = "Timeline xG",
) -> plt.Figure:
    """
    Graphique d'accumulation du xG au fil du match pour deux équipes.

    L'axe x = minute du match (0 à 90+)
    L'axe y = xG cumulé

    Un tir de haute qualité = saut vertical important.
    Un but = marqueur spécial sur la ligne.

    Args:
        df (pd.DataFrame) : DataFrame de tirs d'UN match
        home_team (str)   : nom de l'équipe à domicile
        away_team (str)   : nom de l'équipe à l'extérieur
        title (str)       : titre

    Returns:
        matplotlib.figure.Figure
    """
    fig, ax = plt.subplots(figsize=(12, 5))
    fig.patch.set_facecolor(COLORS["background"])
    ax.set_facecolor(COLORS["panel"])

    def plot_team_xg(team_name, color, label):
        team_shots = df[df["team"].str.contains(team_name, case=False, na=False)].sort_values("minute")
        if team_shots.empty:
            return

        minutes = [0] + list(team_shots["minute"]) + [90]
        xg_cum  = [0] + list(team_shots["xg"].cumsum()) + [team_shots["xg"].sum()]

        # Ligne d'accumulation
        ax.step(minutes, xg_cum, where="post", color=color, linewidth=2.2,
                label=f"{label} ({xg_cum[-1]:.2f} xG)", alpha=0.9)

        # Zone remplie sous la courbe
        ax.fill_between(minutes, xg_cum, step="post", alpha=0.12, color=color)

        # Marqueurs de buts
        goals = team_shots[team_shots["is_goal"]]
        for _, g in goals.iterrows():
            xg_at_goal = team_shots[team_shots["minute"] <= g["minute"]]["xg"].sum()
            ax.plot(g["minute"], xg_at_goal, marker="*", markersize=14,
                    color=COLORS["goal"], zorder=6,
                    path_effects=[pe.withStroke(linewidth=2, foreground=COLORS["background"])])
            ax.text(g["minute"], xg_at_goal + 0.04, "⚽", fontsize=9,
                    ha="center", va="bottom", color=COLORS["goal"])

    plot_team_xg(home_team, COLORS["accent_blue"],   home_team.split()[-1])
    plot_team_xg(away_team, COLORS["accent_purple"],  away_team.split()[-1])

    # Lignes de mi-temps
    ax.axvline(45, color=COLORS["text_muted"], linestyle=":", linewidth=1, alpha=0.5)
    ax.text(45.5, ax.get_ylim()[1] * 0.95, "Mi-temps",
            fontsize=7.5, color=COLORS["text_muted"], va="top")

    ax.set_xlabel("Minute", color=COLORS["text_muted"])
    ax.set_ylabel("xG cumulé", color=COLORS["text_muted"])
    ax.set_xlim(0, df["minute"].max() + 3)
    ax.legend(facecolor=COLORS["panel"], edgecolor=COLORS["grid"],
              labelcolor=COLORS["text"], fontsize=9)
    ax.grid(alpha=0.25)
    ax.spines[["top", "right"]].set_visible(False)

    _fig_title(fig, title, subtitle="Accumulation xG au fil du match  |  ⭐ = but")
    _watermark(fig)
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    return fig


# ============================================================
# TEST RAPIDE
# ============================================================

if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, ".")
    from src.data_loader import load_matches, load_shots_from_match
    from src.metrics     import player_shooting_profile

    os.makedirs("data/test_outputs", exist_ok=True)

    print("🎨 Test de viz.py...\n")
    matches  = load_matches(competition_id=11, season_id=90)
    match    = matches.iloc[0]
    shots    = load_shots_from_match(match["match_id"])
    profile  = player_shooting_profile(shots)

    print("📍 Génération shot_map...")
    fig = shot_map(shots, title=f"{match['home_team']} vs {match['away_team']} — Shot Map")
    fig.savefig("data/test_outputs/shot_map.png", dpi=120, bbox_inches="tight")
    print("   → data/test_outputs/shot_map.png ✅")

    print("📊 Génération player_xg_bar...")
    fig = player_xg_bar(profile, title="xG vs Buts — match test")
    fig.savefig("data/test_outputs/xg_bar.png", dpi=120, bbox_inches="tight")
    print("   → data/test_outputs/xg_bar.png ✅")

    print("🎯 Génération overperformance_chart...")
    fig = overperformance_chart(profile, title="Overperformance — match test")
    fig.savefig("data/test_outputs/overperformance.png", dpi=120, bbox_inches="tight")
    print("   → data/test_outputs/overperformance.png ✅")

    print("📈 Génération xg_distribution_plot...")
    fig = xg_distribution_plot(shots, title="Distribution xG — match test")
    fig.savefig("data/test_outputs/xg_distribution.png", dpi=120, bbox_inches="tight")
    print("   → data/test_outputs/xg_distribution.png ✅")

    print("🔥 Génération xg_zone_heatmap...")
    fig = xg_zone_heatmap(shots, title="Heatmap xG — match test")
    fig.savefig("data/test_outputs/xg_heatmap.png", dpi=120, bbox_inches="tight")
    print("   → data/test_outputs/xg_heatmap.png ✅")

    print("⏱️ Génération xg_timeline...")
    fig = xg_timeline(shots, match["home_team"], match["away_team"],
                      title=f"{match['home_team']} vs {match['away_team']} — Timeline xG")
    fig.savefig("data/test_outputs/xg_timeline.png", dpi=120, bbox_inches="tight")
    print("   → data/test_outputs/xg_timeline.png ✅")

    print("\n✅ Toutes les visualisations générées dans data/test_outputs/")
