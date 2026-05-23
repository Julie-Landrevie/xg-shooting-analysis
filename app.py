"""
app.py — xG & Shooting Profile Analysis
Dashboard Streamlit interactif
Julie Landrevie — Football Data Analyst

Lancement : streamlit run app.py
"""

import warnings
warnings.filterwarnings("ignore")

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from src.data_loader import (
    list_competitions,
    load_matches,
    load_shots_from_competition,
    filter_shots,
    quick_summary,
)
from src.metrics import (
    player_shooting_profile,
    team_shooting_profile,
    xg_by_zone,
    xg_distribution,
    xg_by_time_period,
    top_shooters,
    compare_players,
)
from src.viz import (
    shot_map,
    player_xg_bar,
    overperformance_chart,
    xg_distribution_plot,
    xg_zone_heatmap,
    xg_timeline,
)

# ============================================================
# CONFIG PAGE
# ============================================================

st.set_page_config(
    page_title="xG & Shooting Analysis",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS — charte graphique cohérente avec viz.py
st.markdown("""
<style>
    /* Fond général */
    .stApp { background-color: #1a1a2e; color: #e2e8f0; }
    section[data-testid="stSidebar"] { background-color: #16213e; }

    /* Header custom */
    .main-header {
        background: linear-gradient(135deg, #16213e 0%, #0f3460 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        border-left: 4px solid #4e9af1;
        margin-bottom: 1.5rem;
    }
    .main-header h1 { color: #e2e8f0; margin: 0; font-size: 1.8rem; }
    .main-header p  { color: #94a3b8; margin: 0.3rem 0 0; font-size: 0.95rem; }

    /* Metric cards */
    .metric-card {
        background: #16213e;
        border: 1px solid #2d3748;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        text-align: center;
    }
    .metric-value { font-size: 2rem; font-weight: 700; color: #4e9af1; }
    .metric-goal  { font-size: 2rem; font-weight: 700; color: #f59e0b; }
    .metric-over  { font-size: 2rem; font-weight: 700; color: #10b981; }
    .metric-label { font-size: 0.8rem; color: #94a3b8; margin-top: 0.2rem; }

    /* Section titles */
    .section-title {
        font-size: 1.1rem; font-weight: 600;
        color: #4e9af1; margin: 1.2rem 0 0.6rem;
        border-bottom: 1px solid #2d3748; padding-bottom: 0.4rem;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { background-color: #16213e; border-radius: 8px; }
    .stTabs [data-baseweb="tab"] { color: #94a3b8; }
    .stTabs [aria-selected="true"] { color: #4e9af1 !important; }

    /* Dataframe */
    .stDataFrame { border-radius: 8px; }

    /* Selectbox / inputs */
    .stSelectbox label, .stSlider label { color: #94a3b8 !important; }

    /* Footer */
    .footer {
        text-align: center; color: #475569;
        font-size: 0.75rem; margin-top: 3rem;
        padding-top: 1rem; border-top: 1px solid #2d3748;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# CACHE — évite de re-télécharger à chaque interaction
# ============================================================

@st.cache_data(show_spinner=False)
def get_competitions():
    return list_competitions()

@st.cache_data(show_spinner=False)
def get_matches(competition_id, season_id):
    return load_matches(competition_id, season_id)

@st.cache_data(show_spinner=False)
def get_shots(competition_id, season_id):
    return load_shots_from_competition(
        competition_id=competition_id,
        season_id=season_id,
        use_cache=True,
        verbose=False,
    )


# ============================================================
# SIDEBAR — Sélecteurs globaux
# ============================================================

with st.sidebar:
    st.markdown("## ⚽ xG Analysis")
    st.markdown("*Julie Landrevie — Football Data Analyst*")
    st.divider()

    # Chargement des compétitions
    comps_df = get_competitions()
    comp_labels = (comps_df["competition_name"] + " — " + comps_df["season_name"]).tolist()

    # Compétition par défaut : La Liga 2020/2021
    default_idx = next(
        (i for i, l in enumerate(comp_labels) if "Liga" in l and "2020" in l), 0
    )

    selected_label = st.selectbox(
        "📋 Compétition",
        options=comp_labels,
        index=default_idx,
    )

    selected_row = comps_df[
        (comps_df["competition_name"] + " — " + comps_df["season_name"]) == selected_label
    ].iloc[0]

    comp_id   = int(selected_row["competition_id"])
    season_id = int(selected_row["season_id"])

    st.divider()

    # Chargement des données avec spinner
    with st.spinner("Chargement des données..."):
        shots_all = get_shots(comp_id, season_id)

    if shots_all.empty:
        st.error("Aucune donnée disponible pour cette compétition.")
        st.stop()

    # Normalisation des noms pour l'affichage
    from src.viz import normalize_names_column
    shots_all = normalize_names_column(shots_all)

    # Filtre équipe
    teams_list = sorted(shots_all["team"].dropna().unique().tolist())
    selected_team = st.selectbox("🏟️ Équipe", options=["Toutes les équipes"] + teams_list)

    # Filtre joueur (dépend de l'équipe choisie)
    if selected_team != "Toutes les équipes":
        players_list = sorted(
            shots_all[shots_all["team"] == selected_team]["player"].dropna().unique().tolist()
        )
    else:
        players_list = sorted(shots_all["player"].dropna().unique().tolist())

    selected_player = st.selectbox("👤 Joueur", options=["Tous les joueurs"] + players_list)

    st.divider()

    # Navigation entre onglets (info)
    st.markdown("### 📌 Pages")
    st.markdown("""
    - **Vue d'ensemble** — KPIs & résumé
    - **Shot Map** — tirs sur le terrain
    - **Profil tireur** — xG vs buts
    - **Overperformance** — sur/sous-perf
    - **Zones** — heatmap & stats
    - **Distribution** — qualité occasions
    - **Timeline** — xG par minute
    - **Comparaison** — face-à-face
    """)

    st.divider()
    st.caption("📊 Données : StatsBomb Open Data")
    st.caption("🛠️ Python · mplsoccer · Streamlit")


# ============================================================
# FILTRAGE selon sélections sidebar
# ============================================================

shots = shots_all.copy()

if selected_team != "Toutes les équipes":
    shots = shots[shots["team"] == selected_team]

if selected_player != "Tous les joueurs":
    shots = shots[shots["player"] == selected_player]

# Titre du contexte actuel
context_label = selected_label
if selected_team != "Toutes les équipes":
    context_label += f" · {selected_team}"
if selected_player != "Tous les joueurs":
    context_label += f" · {selected_player}"


# ============================================================
# HEADER
# ============================================================

st.markdown(f"""
<div class="main-header">
    <h1>⚽ xG & Shooting Profile Analysis</h1>
    <p>{context_label} &nbsp;|&nbsp; {len(shots)} tirs analysés</p>
</div>
""", unsafe_allow_html=True)


# ============================================================
# ONGLETS PRINCIPAUX
# ============================================================

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "📊 Vue d'ensemble",
    "🗺️ Shot Map",
    "👤 Profil tireur",
    "🎯 Overperformance",
    "🔥 Zones",
    "📈 Distribution",
    "⏱️ Timeline",
    "⚖️ Comparaison",
])


# ──────────────────────────────────────────────────────────────
# TAB 1 : VUE D'ENSEMBLE
# ──────────────────────────────────────────────────────────────

with tab1:
    # Avertissement données partielles StatsBomb
    n_matches = shots_all["match_id"].nunique()
    st.info(
        f"ℹ️ **Données partielles** — StatsBomb Open Data couvre **{n_matches} matchs** "
        f"pour cette compétition/saison (principalement les matchs d'une équipe par compétition, "
        f"ex : Barcelona pour La Liga). Les classements reflètent cet échantillon, pas la saison entière."
    )
    if shots.empty:
        st.warning("Aucun tir pour cette sélection.")
    else:
        n_shots   = len(shots)
        n_goals   = int(shots["is_goal"].sum())
        xg_total  = shots["xg"].sum()
        conv_real = n_goals / n_shots * 100
        overperf  = n_goals - xg_total
        on_target = int(shots["outcome"].isin(["Goal", "Saved"]).sum())

        # KPIs
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        with c1:
            st.markdown(f'<div class="metric-card"><div class="metric-value">{n_shots}</div><div class="metric-label">Tirs</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="metric-card"><div class="metric-goal">{n_goals}</div><div class="metric-label">Buts</div></div>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div class="metric-card"><div class="metric-value">{xg_total:.2f}</div><div class="metric-label">xG total</div></div>', unsafe_allow_html=True)
        with c4:
            color_class = "metric-over" if overperf >= 0 else "metric-value"
            st.markdown(f'<div class="metric-card"><div class="{color_class}">{overperf:+.2f}</div><div class="metric-label">Overperf.</div></div>', unsafe_allow_html=True)
        with c5:
            st.markdown(f'<div class="metric-card"><div class="metric-value">{conv_real:.1f}%</div><div class="metric-label">Conversion</div></div>', unsafe_allow_html=True)
        with c6:
            ot_rate = on_target / n_shots * 100
            st.markdown(f'<div class="metric-card"><div class="metric-value">{ot_rate:.1f}%</div><div class="metric-label">Cadrés</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        col_left, col_right = st.columns([1, 1])

        with col_left:
            st.markdown('<div class="section-title">Répartition des résultats</div>', unsafe_allow_html=True)
            outcome_counts = shots["outcome"].value_counts().reset_index()
            outcome_counts.columns = ["Résultat", "Nombre"]
            outcome_counts["% du total"] = (outcome_counts["Nombre"] / n_shots * 100).round(1)
            st.dataframe(outcome_counts, use_container_width=True, hide_index=True)

        with col_right:
            st.markdown('<div class="section-title">Répartition par partie du corps</div>', unsafe_allow_html=True)
            body_counts = shots["body_part"].value_counts().reset_index()
            body_counts.columns = ["Partie du corps", "Tirs"]
            body_counts["Buts"] = shots[shots["is_goal"]]["body_part"].value_counts().reindex(body_counts["Partie du corps"]).fillna(0).astype(int).values
            body_counts["xG"] = shots.groupby("body_part")["xg"].sum().reindex(body_counts["Partie du corps"]).round(2).values
            st.dataframe(body_counts, use_container_width=True, hide_index=True)

        # Top 5 joueurs si on est sur une équipe entière
        if selected_player == "Tous les joueurs":
            st.markdown('<div class="section-title">Top 10 tireurs (par xG)</div>', unsafe_allow_html=True)
            profile_all = player_shooting_profile(shots)
            top10 = profile_all[["player", "team", "shots", "goals", "xg", "overperformance", "xg_per_shot", "on_target_rate"]].head(10)
            top10.columns = ["Joueur", "Équipe", "Tirs", "Buts", "xG", "Overperf.", "xG/tir", "% Cadrés"]
            st.dataframe(top10, use_container_width=True, hide_index=True)


# ──────────────────────────────────────────────────────────────
# TAB 2 : SHOT MAP
# ──────────────────────────────────────────────────────────────

with tab2:
    if shots.empty:
        st.warning("Aucun tir pour cette sélection.")
    else:
        c1, c2 = st.columns([3, 1])
        with c2:
            st.markdown("#### Options")
            goals_only = st.checkbox("Buts uniquement", value=False)
            st.markdown("---")
            st.markdown("""
**Lecture :**
- 🟡 **Or** = but marqué
- ⬛ Gris = non converti
- ⬜ **Contour blanc** = tir cadré
- **Taille** = valeur xG
            """)

        with c1:
            team_label = selected_team if selected_team != "Toutes les équipes" else "Toutes équipes"
            player_label = f" — {selected_player}" if selected_player != "Tous les joueurs" else ""
            title = f"{team_label}{player_label} — Shot Map"

            fig = shot_map(shots, title=title, show_goals_only=goals_only)
            st.pyplot(fig, use_container_width=True)
            plt.close("all")


# ──────────────────────────────────────────────────────────────
# TAB 3 : PROFIL TIREUR
# ──────────────────────────────────────────────────────────────

with tab3:
    if shots.empty:
        st.warning("Aucun tir pour cette sélection.")
    else:
        profile = player_shooting_profile(shots)

        c1, c2 = st.columns([3, 1])
        with c2:
            st.markdown("#### Options")
            metric_options = {
                "xG total": "xg",
                "Buts": "goals",
                "Tirs": "shots",
                "xG par tir": "xg_per_shot",
                "% Cadrés": "on_target_rate",
                "Big chances": "big_chances",
            }
            selected_metric_label = st.selectbox("Trier par", list(metric_options.keys()))
            selected_metric = metric_options[selected_metric_label]
            top_n = st.slider("Nombre de joueurs", min_value=5, max_value=20, value=12)
            min_shots_filter = st.slider("Tirs minimum", min_value=1, max_value=20, value=5)

        with c1:
            filtered_profile = profile[profile["shots"] >= min_shots_filter]
            fig = player_xg_bar(
                filtered_profile,
                top_n=top_n,
                metric=selected_metric,
                title=f"xG vs Buts — Top {top_n} par {selected_metric_label}"
            )
            st.pyplot(fig, use_container_width=True)
            plt.close("all")

        st.markdown('<div class="section-title">Tableau complet</div>', unsafe_allow_html=True)
        display_cols = ["player", "team", "shots", "goals", "xg", "xg_per_shot",
                        "overperformance", "on_target_rate", "big_chances", "big_chances_scored"]
        display_labels = ["Joueur", "Équipe", "Tirs", "Buts", "xG", "xG/tir",
                          "Overperf.", "% Cadrés", "Big chances", "Big ch. scorées"]
        df_display = filtered_profile[display_cols].copy()
        df_display.columns = display_labels
        st.dataframe(df_display, use_container_width=True, hide_index=True)


# ──────────────────────────────────────────────────────────────
# TAB 4 : OVERPERFORMANCE
# ──────────────────────────────────────────────────────────────

with tab4:
    if shots.empty:
        st.warning("Aucun tir pour cette sélection.")
    else:
        profile = player_shooting_profile(shots)

        c1, c2 = st.columns([3, 1])
        with c2:
            st.markdown("#### Options")
            top_n_over = st.slider("Nombre de joueurs", min_value=5, max_value=25, value=15, key="over_n")
            min_shots_over = st.slider("Tirs minimum", min_value=1, max_value=20, value=5, key="over_min")
            st.markdown("---")
            st.markdown("""
**Overperformance = Buts − xG**

🟢 **Positif** → marque plus que prévu  
→ Finisseur efficace

🔴 **Négatif** → marque moins que prévu  
→ Manque d'efficacité ou malchance
            """)

        with c1:
            filtered = profile[profile["shots"] >= min_shots_over]
            fig = overperformance_chart(
                filtered,
                top_n=top_n_over,
                title=f"Overperformance xG — Top {top_n_over} (min. {min_shots_over} tirs)"
            )
            st.pyplot(fig, use_container_width=True)
            plt.close("all")

        # Podiums
        st.markdown('<div class="section-title">Podiums</div>', unsafe_allow_html=True)
        col_pos, col_neg = st.columns(2)

        with col_pos:
            st.markdown("🟢 **Les plus efficaces (Buts > xG)**")
            best = filtered.sort_values("overperformance", ascending=False).head(5)
            st.dataframe(
                best[["player", "goals", "xg", "overperformance"]].rename(
                    columns={"player": "Joueur", "goals": "Buts", "xg": "xG", "overperformance": "Overperf."}
                ),
                use_container_width=True, hide_index=True
            )

        with col_neg:
            st.markdown("🔴 **Les plus malchanceux (Buts < xG)**")
            worst = filtered.sort_values("overperformance").head(5)
            st.dataframe(
                worst[["player", "goals", "xg", "overperformance"]].rename(
                    columns={"player": "Joueur", "goals": "Buts", "xg": "xG", "overperformance": "Overperf."}
                ),
                use_container_width=True, hide_index=True
            )


# ──────────────────────────────────────────────────────────────
# TAB 5 : ZONES
# ──────────────────────────────────────────────────────────────

with tab5:
    if shots.empty:
        st.warning("Aucun tir pour cette sélection.")
    else:
        col_map, col_table = st.columns([3, 2])

        with col_map:
            team_label = selected_team if selected_team != "Toutes les équipes" else "Toutes équipes"
            fig = xg_zone_heatmap(shots, title=f"{team_label} — Heatmap xG par zone")
            st.pyplot(fig, use_container_width=True)
            plt.close("all")

        with col_table:
            st.markdown('<div class="section-title">Stats par zone</div>', unsafe_allow_html=True)
            zones = xg_by_zone(shots)
            if not zones.empty:
                zones_display = zones.copy()
                zones_display.columns = ["Zone", "Tirs", "Buts", "xG total", "xG moyen", "Conversion %"]
                st.dataframe(zones_display, use_container_width=True, hide_index=True)

                # Zone la plus dangereuse
                best_zone = zones.iloc[0]
                st.info(f"🔥 Zone la plus dangereuse : **{best_zone['zone_name']}** — xG moyen : **{best_zone['xg_mean']:.3f}**")


# ──────────────────────────────────────────────────────────────
# TAB 6 : DISTRIBUTION xG
# ──────────────────────────────────────────────────────────────

with tab6:
    if shots.empty:
        st.warning("Aucun tir pour cette sélection.")
    else:
        col_chart, col_info = st.columns([3, 1])

        with col_info:
            st.markdown("#### Lecture")
            st.markdown("""
🔵 **Bleu** = tous les tirs  
🟡 **Or** = buts marqués  
🟣 **Tiret violet** = xG moyen

**Profils typiques :**
- Beaucoup de faibles xG → tirs de loin
- Pics à droite → attaquant de surface
- Buts dans les hauts xG → finisseur sur grosses occasions
            """)

            dist_table = xg_distribution(shots)
            dist_table = dist_table[dist_table["shots"] > 0]
            st.markdown('<div class="section-title">Table xG</div>', unsafe_allow_html=True)
            st.dataframe(
                dist_table.rename(columns={
                    "xg_range": "Tranche xG",
                    "shots": "Tirs",
                    "goals": "Buts",
                    "xg_total": "xG",
                    "conversion": "Conv. %"
                }),
                use_container_width=True,
                hide_index=True,
            )

        with col_chart:
            player_label = selected_player if selected_player != "Tous les joueurs" else ""
            team_label   = selected_team   if selected_team   != "Toutes les équipes" else "Toutes équipes"
            context_title = f"{team_label}{' · ' + player_label if player_label else ''}"

            fig = xg_distribution_plot(shots, title=f"Distribution xG — {context_title}")
            st.pyplot(fig, use_container_width=True)
            plt.close("all")


# ──────────────────────────────────────────────────────────────
# TAB 7 : TIMELINE xG
# ──────────────────────────────────────────────────────────────

with tab7:
    matches_df = get_matches(comp_id, season_id)

    if matches_df.empty:
        st.warning("Aucun match disponible.")
    else:
        # Sélecteur de match
        match_labels = (
            matches_df["match_date"].astype(str) + " — " +
            matches_df["home_team"] + " vs " +
            matches_df["away_team"] + "  (" +
            matches_df["home_score"].astype(str) + "-" +
            matches_df["away_score"].astype(str) + ")"
        ).tolist()

        if selected_team != "Toutes les équipes":
            mask = (
                matches_df["home_team"].str.contains(selected_team, case=False) |
                matches_df["away_team"].str.contains(selected_team, case=False)
            )
            filtered_matches = matches_df[mask]
            filtered_labels  = [l for l, m in zip(match_labels, mask) if m]
        else:
            filtered_matches = matches_df
            filtered_labels  = match_labels

        if filtered_matches.empty:
            st.warning(f"Aucun match trouvé pour {selected_team}.")
        else:
            selected_match_label = st.selectbox("Match", options=filtered_labels)
            match_idx = filtered_labels.index(selected_match_label)
            match_row = filtered_matches.iloc[match_idx]

            # Chargement des tirs du match sélectionné
            with st.spinner("Chargement du match..."):
                @st.cache_data(show_spinner=False)
                def get_match_shots(match_id):
                    from src.data_loader import load_shots_from_match
                    return load_shots_from_match(match_id)

                match_shots = get_match_shots(int(match_row["match_id"]))

            if not match_shots.empty:
                col_chart, col_info = st.columns([4, 1])

                with col_info:
                    st.markdown("#### Résumé")
                    home = match_row["home_team"]
                    away = match_row["away_team"]

                    home_xg = match_shots[match_shots["team"] == home]["xg"].sum()
                    away_xg = match_shots[match_shots["team"] == away]["xg"].sum()
                    home_g  = int(match_row["home_score"])
                    away_g  = int(match_row["away_score"])

                    st.markdown(f"**{home.split()[-1]}**")
                    st.markdown(f"Buts : **{home_g}** | xG : **{home_xg:.2f}**")
                    st.markdown("---")
                    st.markdown(f"**{away.split()[-1]}**")
                    st.markdown(f"Buts : **{away_g}** | xG : **{away_xg:.2f}**")
                    st.markdown("---")

                    winner_xg = home if home_xg > away_xg else away
                    st.markdown(f"🏆 Dominateur xG : **{winner_xg.split()[-1]}**")

                with col_chart:
                    fig = xg_timeline(
                        match_shots,
                        home_team=match_row["home_team"],
                        away_team=match_row["away_team"],
                        title=f"{match_row['home_team']} {home_g}–{away_g} {match_row['away_team']}"
                    )
                    st.pyplot(fig, use_container_width=True)
                    plt.close("all")

                # Stats minute par minute
                st.markdown('<div class="section-title">xG par tranche de 15 minutes</div>', unsafe_allow_html=True)
                col_h, col_a = st.columns(2)
                with col_h:
                    st.markdown(f"**{match_row['home_team']}**")
                    tempo_home = xg_by_time_period(match_shots[match_shots["team"] == match_row["home_team"]])
                    if not tempo_home.empty:
                        st.dataframe(tempo_home[["period","shots","goals","xg_total"]].rename(
                            columns={"period":"Période","shots":"Tirs","goals":"Buts","xg_total":"xG"}),
                            use_container_width=True, hide_index=True)
                with col_a:
                    st.markdown(f"**{match_row['away_team']}**")
                    tempo_away = xg_by_time_period(match_shots[match_shots["team"] == match_row["away_team"]])
                    if not tempo_away.empty:
                        st.dataframe(tempo_away[["period","shots","goals","xg_total"]].rename(
                            columns={"period":"Période","shots":"Tirs","goals":"Buts","xg_total":"xG"}),
                            use_container_width=True, hide_index=True)


# ──────────────────────────────────────────────────────────────
# TAB 8 : COMPARAISON JOUEURS
# ──────────────────────────────────────────────────────────────

with tab8:
    st.markdown("#### Comparaison face-à-face entre deux joueurs")

    profile_all = player_shooting_profile(shots_all)
    players_ranked = profile_all[profile_all["shots"] >= 5]["player"].tolist()

    if len(players_ranked) < 2:
        st.warning("Pas assez de joueurs avec suffisamment de tirs.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            p1 = st.selectbox("Joueur 1", options=players_ranked, index=0, key="comp_p1")
        with col2:
            default_p2 = 1 if len(players_ranked) > 1 else 0
            p2 = st.selectbox("Joueur 2", options=players_ranked, index=default_p2, key="comp_p2")

        if p1 == p2:
            st.warning("Sélectionne deux joueurs différents.")
        else:
            try:
                comp_table = compare_players(shots_all, p1, p2)
                st.dataframe(comp_table, use_container_width=True, hide_index=True)

                # Shot maps côte à côte
                st.markdown('<div class="section-title">Shot Maps comparées</div>', unsafe_allow_html=True)
                col_a, col_b = st.columns(2)

                with col_a:
                    shots_p1 = filter_shots(shots_all, player=p1)
                    fig1 = shot_map(shots_p1, title=p1.split()[-1])
                    st.pyplot(fig1, use_container_width=True)
                    plt.close("all")

                with col_b:
                    shots_p2 = filter_shots(shots_all, player=p2)
                    fig2 = shot_map(shots_p2, title=p2.split()[-1])
                    st.pyplot(fig2, use_container_width=True)
                    plt.close("all")

            except ValueError as e:
                st.error(str(e))


# ============================================================
# FOOTER
# ============================================================

st.markdown("""
<div class="footer">
    Julie Landrevie — Football Data Analyst &nbsp;|&nbsp;
    xG & Shooting Profile Analysis &nbsp;|&nbsp;
    StatsBomb Open Data &nbsp;|&nbsp;
    Python · mplsoccer · Streamlit
</div>
""", unsafe_allow_html=True)
