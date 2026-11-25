"""
app.py — xG & Shooting Profile Analysis (français / anglais, clair / sombre)
Julie Landrevie — Data & performance football
Charte commune : jl_ui.py et .streamlit/config.toml (figures : src/viz.py).

Lancement : streamlit run app.py
"""

import warnings

import streamlit as st

warnings.filterwarnings("ignore")

from jl_ui import footer, fr_num, header, is_dark, kpi, lang, note, setup, t  # noqa: E402

setup("xG & Shooting — Julie Landrevie", "xG & Shooting — Julie Landrevie", icon="⚽")

import matplotlib.pyplot as plt  # noqa: E402

from src import viz  # noqa: E402
from src.data_loader import filter_shots, list_competitions, load_matches, load_shots_from_competition  # noqa: E402
from src.metrics import compare_players, player_shooting_profile, xg_by_time_period, xg_by_zone, xg_distribution  # noqa: E402
from src.viz import (normalize_names_column, overperformance_chart, player_xg_bar, shot_map,  # noqa: E402
                     xg_distribution_plot, xg_timeline, xg_zone_heatmap)

viz.set_lang(lang())
viz.set_theme(is_dark())

ALL = "__all__"
OUTCOME_FR = {"Goal": "But", "Saved": "Arrêté", "Off T": "Hors cadre", "Blocked": "Contré", "Wayward": "Non cadré (raté)",
              "Post": "Poteau", "Saved Off Target": "Arrêté (hors cadre)", "Saved to Post": "Arrêté sur le poteau"}
BODY_FR = {"Right Foot": "Pied droit", "Left Foot": "Pied gauche", "Head": "Tête", "Other": "Autre"}
ZONE_EN = {"Inconnu": "Unknown", "Hors surface lointaine": "Long range (outside the box)",
           "Penalty / but vide": "Penalty / open goal", "Surface centrale (6 yards)": "Central box (6-yard area)",
           "Surface gauche": "Left side of the box", "Surface droite": "Right side of the box",
           "Entrée de surface centrale": "Edge of the box, central", "Entrée de surface gauche": "Edge of the box, left",
           "Entrée de surface droite": "Edge of the box, right"}
METRIC_NAMES = {"shots": ("Tirs", "Shots"), "goals": ("Buts", "Goals"), "xg": ("xG", "xG"),
                "xg_per_shot": ("xG par tir", "xG per shot"), "conversion_rate": ("Conversion", "Conversion"),
                "overperformance": ("Buts − xG", "Goals − xG"), "shots_on_target": ("Tirs cadrés", "Shots on target"),
                "on_target_rate": ("Taux de cadrage", "On-target rate"), "big_chances": ("Grosses occasions", "Big chances"),
                "big_chances_scored": ("Grosses occasions converties", "Big chances scored"),
                "headed_shots": ("Tirs de la tête", "Headers"), "left_foot_shots": ("Tirs pied gauche", "Left-foot shots"),
                "right_foot_shots": ("Tirs pied droit", "Right-foot shots"), "player": ("Joueur", "Player"),
                "team": ("Équipe", "Team")}


def tr(d, v):
    """Traduit une valeur de données (StatsBomb en anglais, zones en français)."""
    return t(d.get(v, v), v) if d is not ZONE_EN else t(v, ZONE_EN.get(v, v))


def table(df, cols):
    out = df[cols].copy()
    out.columns = [t(*METRIC_NAMES[c]) for c in cols]
    st.dataframe(out, width="stretch", hide_index=True)


def show(fig):
    st.pyplot(fig, width="stretch")
    plt.close("all")


# ============================================================
# CACHE
# ============================================================

@st.cache_data(show_spinner=False)
def get_competitions():
    return list_competitions()


@st.cache_data(show_spinner=False)
def get_matches(competition_id, season_id):
    return load_matches(competition_id, season_id)


@st.cache_data(show_spinner=False)
def get_shots(competition_id, season_id):
    return load_shots_from_competition(competition_id=competition_id, season_id=season_id, use_cache=True, verbose=False)


@st.cache_data(show_spinner=False)
def get_match_shots(match_id):
    from src.data_loader import load_shots_from_match
    return load_shots_from_match(match_id)


# ============================================================
# BARRE LATÉRALE
# ============================================================

with st.sidebar:
    st.markdown("### xG & Shooting")
    comps_df = get_competitions()
    comp_labels = (comps_df["competition_name"] + " — " + comps_df["season_name"]).tolist()
    default_idx = next((i for i, lab in enumerate(comp_labels) if "Liga" in lab and "2020/2021" in lab), 0)
    selected_label = st.selectbox(t("Compétition", "Competition"), options=comp_labels, index=default_idx)
    selected_row = comps_df[(comps_df["competition_name"] + " — " + comps_df["season_name"]) == selected_label].iloc[0]
    comp_id, season_id = int(selected_row["competition_id"]), int(selected_row["season_id"])

    with st.spinner(t("Chargement des données…", "Loading data…")):
        shots_all = get_shots(comp_id, season_id)
    if shots_all.empty:
        st.error(t("Aucune donnée disponible pour cette compétition.", "No data available for this competition."))
        st.stop()
    shots_all = normalize_names_column(shots_all)

    teams_list = sorted(shots_all["team"].dropna().unique().tolist())
    selected_team = st.selectbox(t("Équipe", "Team"), options=[ALL] + teams_list,
                                 format_func=lambda v: t("Toutes les équipes", "All teams") if v == ALL else v)
    pool = shots_all if selected_team == ALL else shots_all[shots_all["team"] == selected_team]
    players_list = sorted(pool["player"].dropna().unique().tolist())
    selected_player = st.selectbox(t("Joueur", "Player"), options=[ALL] + players_list,
                                   format_func=lambda v: t("Tous les joueurs", "All players") if v == ALL else v)
    st.caption(t("Données : StatsBomb Open Data · Python, mplsoccer, Streamlit",
                 "Data: StatsBomb Open Data · Python, mplsoccer, Streamlit"))


# ============================================================
# FILTRAGE
# ============================================================

shots = shots_all.copy()
if selected_team != ALL:
    shots = shots[shots["team"] == selected_team]
if selected_player != ALL:
    shots = shots[shots["player"] == selected_player]

context_label = selected_label
if selected_team != ALL:
    context_label += f" · {selected_team}"
if selected_player != ALL:
    context_label += f" · {selected_player}"
team_label = selected_team if selected_team != ALL else t("Toutes les équipes", "All teams")

header(t("xG et profils de tireurs", "xG and shooting profiles"),
       f"{context_label} · {len(shots)} {t('tirs analysés', 'shots analysed')}")

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    t("Vue d’ensemble", "Overview"), t("Carte des tirs", "Shot map"), t("Profil tireur", "Shooter profile"),
    t("Buts − xG", "Goals − xG"), t("Zones", "Zones"), t("Distribution", "Distribution"),
    t("Chronologie", "Timeline"), t("Comparaison", "Comparison")])


# ── 1. VUE D'ENSEMBLE ───────────────────────────────────────
with tab1:
    n_matches = shots_all["match_id"].nunique()
    note(t(f"<b>Données partielles</b> : StatsBomb Open Data couvre <b>{n_matches} matchs</b> pour cette compétition et cette "
           "saison (souvent les matchs d’une seule équipe, par exemple Barcelone pour la Liga). Les classements reflètent cet "
           "échantillon, pas la saison entière.",
           f"<b>Partial data</b>: StatsBomb Open Data covers <b>{n_matches} matches</b> for this competition and season (often "
           "one team’s matches, e.g. Barcelona for La Liga). Rankings reflect this sample, not the whole season."), warn=True)
    if shots.empty:
        st.warning(t("Aucun tir pour cette sélection.", "No shots for this selection."))
    else:
        n_shots = len(shots)
        n_goals = int(shots["is_goal"].sum())
        xg_total = shots["xg"].sum()
        overperf = n_goals - xg_total
        on_target = int(shots["outcome"].isin(["Goal", "Saved"]).sum())
        c = st.columns(6)
        kpi(c[0], str(n_shots), t("Tirs", "Shots"))
        kpi(c[1], str(n_goals), t("Buts", "Goals"))
        kpi(c[2], fr_num(xg_total, 2), t("xG total", "Total xG"))
        kpi(c[3], ("+" if overperf >= 0 else "−") + fr_num(abs(overperf), 2), t("Buts − xG", "Goals − xG"), accent=True)
        kpi(c[4], fr_num(n_goals / n_shots * 100, 1, pct=True), t("Conversion", "Conversion"))
        kpi(c[5], fr_num(on_target / n_shots * 100, 1, pct=True), t("Tirs cadrés", "On target"))
        st.write("")

        col_left, col_right = st.columns(2)
        with col_left:
            st.markdown(f"**{t('Issue des tirs', 'Shot outcomes')}**")
            oc = shots["outcome"].value_counts().reset_index()
            oc.columns = ["o", "n"]
            st.dataframe({t("Issue", "Outcome"): [tr(OUTCOME_FR, v) for v in oc["o"]],
                          t("Tirs", "Shots"): oc["n"].tolist(),
                          t("Part", "Share"): [fr_num(v / n_shots * 100, 1, pct=True) for v in oc["n"]]},
                         width="stretch", hide_index=True)
        with col_right:
            st.markdown(f"**{t('Partie du corps', 'Body part')}**")
            bc = shots["body_part"].value_counts()
            goals_bp = shots[shots["is_goal"]]["body_part"].value_counts()
            xg_bp = shots.groupby("body_part")["xg"].sum()
            st.dataframe({t("Partie du corps", "Body part"): [tr(BODY_FR, v) for v in bc.index],
                          t("Tirs", "Shots"): bc.tolist(),
                          t("Buts", "Goals"): [int(goals_bp.get(v, 0)) for v in bc.index],
                          "xG": [fr_num(xg_bp.get(v, 0), 2) for v in bc.index]},
                         width="stretch", hide_index=True)

        if selected_player == ALL:
            st.markdown(f"**{t('10 premiers tireurs (par xG)', 'Top 10 shooters (by xG)')}**")
            table(player_shooting_profile(shots).head(10),
                  ["player", "team", "shots", "goals", "xg", "overperformance", "xg_per_shot", "on_target_rate"])


# ── 2. CARTE DES TIRS ───────────────────────────────────────
with tab2:
    if shots.empty:
        st.warning(t("Aucun tir pour cette sélection.", "No shots for this selection."))
    else:
        c1, c2 = st.columns([3, 1])
        with c2:
            goals_only = st.checkbox(t("Buts uniquement", "Goals only"), value=False)
            st.markdown(t("**Lecture**\n- rouille : but\n- gris : non converti\n- contour marqué : tir cadré\n- taille : valeur xG",
                          "**How to read it**\n- rust: goal\n- grey: not scored\n- bold outline: on target\n- size: xG value"))
        with c1:
            player_label = f" · {selected_player}" if selected_player != ALL else ""
            show(shot_map(shots, title=f"{team_label}{player_label}", show_goals_only=goals_only))


# ── 3. PROFIL TIREUR ────────────────────────────────────────
with tab3:
    if shots.empty:
        st.warning(t("Aucun tir pour cette sélection.", "No shots for this selection."))
    else:
        profile = player_shooting_profile(shots)
        c1, c2 = st.columns([3, 1])
        with c2:
            metric_keys = ["xg", "goals", "shots", "xg_per_shot", "on_target_rate", "big_chances"]
            selected_metric = st.selectbox(t("Trier par", "Sort by"), metric_keys, format_func=lambda k: t(*METRIC_NAMES[k]))
            top_n = st.slider(t("Nombre de joueurs", "Number of players"), min_value=5, max_value=20, value=12)
            min_shots_filter = st.slider(t("Tirs minimum", "Minimum shots"), min_value=1, max_value=20, value=5)
        with c1:
            filtered_profile = profile[profile["shots"] >= min_shots_filter]
            show(player_xg_bar(filtered_profile, top_n=top_n, metric=selected_metric,
                               title=t(f"xG et buts : top {top_n} par {t(*METRIC_NAMES[selected_metric]).lower()}",
                                       f"xG and goals: top {top_n} by {t(*METRIC_NAMES[selected_metric]).lower()}")))
        st.markdown(f"**{t('Tableau complet', 'Full table')}**")
        table(filtered_profile, ["player", "team", "shots", "goals", "xg", "xg_per_shot", "overperformance",
                                 "on_target_rate", "big_chances", "big_chances_scored"])


# ── 4. BUTS − xG ────────────────────────────────────────────
with tab4:
    if shots.empty:
        st.warning(t("Aucun tir pour cette sélection.", "No shots for this selection."))
    else:
        profile = player_shooting_profile(shots)
        c1, c2 = st.columns([3, 1])
        with c2:
            top_n_over = st.slider(t("Nombre de joueurs", "Number of players"), min_value=5, max_value=25, value=15, key="over_n")
            min_shots_over = st.slider(t("Tirs minimum", "Minimum shots"), min_value=1, max_value=20, value=5, key="over_min")
            st.markdown(t("**Buts − xG**\n\nPositif (vert d’eau) : marque plus que prévu, finisseur efficace.\n\n"
                          "Négatif (rouille) : marque moins que prévu, manque d’efficacité ou malchance.",
                          "**Goals − xG**\n\nPositive (teal): scores more than expected, an efficient finisher.\n\n"
                          "Negative (rust): scores less than expected, poor finishing or bad luck."))
        with c1:
            filtered = profile[profile["shots"] >= min_shots_over]
            show(overperformance_chart(filtered, top_n=top_n_over,
                                       title=t(f"Buts − xG : top {top_n_over} (au moins {min_shots_over} tirs)",
                                               f"Goals − xG: top {top_n_over} (at least {min_shots_over} shots)")))
        col_pos, col_neg = st.columns(2)
        with col_pos:
            st.markdown(f"**{t('Les plus efficaces (buts > xG)', 'Most efficient (goals > xG)')}**")
            table(filtered.sort_values("overperformance", ascending=False).head(5), ["player", "goals", "xg", "overperformance"])
        with col_neg:
            st.markdown(f"**{t('Les moins efficaces (buts < xG)', 'Least efficient (goals < xG)')}**")
            table(filtered.sort_values("overperformance").head(5), ["player", "goals", "xg", "overperformance"])


# ── 5. ZONES ────────────────────────────────────────────────
with tab5:
    if shots.empty:
        st.warning(t("Aucun tir pour cette sélection.", "No shots for this selection."))
    else:
        col_map, col_table = st.columns([3, 2])
        with col_map:
            show(xg_zone_heatmap(shots, title=t(f"{team_label} : xG par zone", f"{team_label}: xG by zone")))
        with col_table:
            st.markdown(f"**{t('Statistiques par zone', 'Stats by zone')}**")
            zones = xg_by_zone(shots)
            if not zones.empty:
                zd = zones.copy()
                zd.columns = [t("Zone", "Zone"), t("Tirs", "Shots"), t("Buts", "Goals"), t("xG total", "Total xG"),
                              t("xG moyen", "Mean xG"), t("Conversion (%)", "Conversion (%)")]
                zd[t("Zone", "Zone")] = [tr(ZONE_EN, z) for z in zones["zone_name"]]
                st.dataframe(zd, width="stretch", hide_index=True)
                best = zones.iloc[0]
                note(t(f"Zone la plus dangereuse : <b>{best['zone_name']}</b>, xG moyen <b>{fr_num(best['xg_mean'], 3)}</b>.",
                       f"Most dangerous zone: <b>{tr(ZONE_EN, best['zone_name'])}</b>, mean xG <b>{fr_num(best['xg_mean'], 3)}</b>."))


# ── 6. DISTRIBUTION ─────────────────────────────────────────
with tab6:
    if shots.empty:
        st.warning(t("Aucun tir pour cette sélection.", "No shots for this selection."))
    else:
        col_chart, col_info = st.columns([3, 1])
        with col_info:
            st.markdown(t("**Lecture**\n- vert d’eau : tous les tirs\n- rouille : buts\n- tirets : xG moyen\n\n"
                          "**Profils typiques**\n- beaucoup de faibles xG : tirs de loin\n- pic à droite : joueur de surface\n"
                          "- buts dans les hauts xG : finisseur sur grosses occasions",
                          "**How to read it**\n- teal: all shots\n- rust: goals\n- dashed: mean xG\n\n"
                          "**Typical profiles**\n- many low xG: long-range shooting\n- peak on the right: box player\n"
                          "- goals at high xG: big-chance finisher"))
            dist = xg_distribution(shots)
            dist = dist[dist["shots"] > 0].rename(columns={"xg_range": t("Tranche de xG", "xG range"), "shots": t("Tirs", "Shots"),
                                                           "goals": t("Buts", "Goals"), "xg_total": "xG",
                                                           "conversion": t("Conversion (%)", "Conversion (%)")})
            st.dataframe(dist, width="stretch", hide_index=True)
        with col_chart:
            player_label = f" · {selected_player}" if selected_player != ALL else ""
            show(xg_distribution_plot(shots, title=t(f"Distribution des xG : {team_label}{player_label}",
                                                      f"xG distribution: {team_label}{player_label}")))


# ── 7. CHRONOLOGIE ──────────────────────────────────────────
with tab7:
    matches_df = get_matches(comp_id, season_id)
    if matches_df.empty:
        st.warning(t("Aucun match disponible.", "No match available."))
    else:
        if selected_team != ALL:
            m = (matches_df["home_team"].str.contains(selected_team, case=False, regex=False)
                 | matches_df["away_team"].str.contains(selected_team, case=False, regex=False))
            filtered_matches = matches_df[m]
        else:
            filtered_matches = matches_df
        if filtered_matches.empty:
            st.warning(t(f"Aucun match trouvé pour {selected_team}.", f"No match found for {selected_team}."))
        else:
            labels = {int(r["match_id"]): f"{r['match_date']} · {r['home_team']} {r['home_score']}-{r['away_score']} {r['away_team']}"
                      for _, r in filtered_matches.iterrows()}
            mid = st.selectbox(t("Match", "Match"), options=list(labels), format_func=lambda k: labels[k])
            match_row = filtered_matches[filtered_matches["match_id"] == mid].iloc[0]
            with st.spinner(t("Chargement du match…", "Loading the match…")):
                match_shots = get_match_shots(int(mid))
            if not match_shots.empty:
                home, away = match_row["home_team"], match_row["away_team"]
                home_g, away_g = int(match_row["home_score"]), int(match_row["away_score"])
                home_xg = match_shots[match_shots["team"] == home]["xg"].sum()
                away_xg = match_shots[match_shots["team"] == away]["xg"].sum()
                col_chart, col_info = st.columns([4, 1])
                with col_info:
                    kpi(st, f"{home_g} · {fr_num(home_xg, 2)}", f"{home}{t(' :', ':')} {t('buts · xG', 'goals · xG')}")
                    st.write("")
                    kpi(st, f"{away_g} · {fr_num(away_xg, 2)}", f"{away}{t(' :', ':')} {t('buts · xG', 'goals · xG')}")
                with col_chart:
                    show(xg_timeline(match_shots, home_team=home, away_team=away, title=f"{home} {home_g}–{away_g} {away}"))
                st.markdown(f"**{t('xG par tranche de 15 minutes', 'xG per 15-minute period')}**")
                col_h, col_a = st.columns(2)
                for col, team in ((col_h, home), (col_a, away)):
                    with col:
                        st.markdown(team)
                        tempo = xg_by_time_period(match_shots[match_shots["team"] == team])
                        if not tempo.empty:
                            st.dataframe(tempo[["period", "shots", "goals", "xg_total"]].rename(columns={
                                "period": t("Période", "Period"), "shots": t("Tirs", "Shots"),
                                "goals": t("Buts", "Goals"), "xg_total": "xG"}), width="stretch", hide_index=True)


# ── 8. COMPARAISON ──────────────────────────────────────────
with tab8:
    st.markdown(f"**{t('Comparaison entre deux joueurs', 'Head-to-head between two players')}**")
    profile_all = player_shooting_profile(shots_all)
    players_ranked = profile_all[profile_all["shots"] >= 5]["player"].tolist()
    if len(players_ranked) < 2:
        st.warning(t("Pas assez de joueurs avec suffisamment de tirs.", "Not enough players with enough shots."))
    else:
        col1, col2 = st.columns(2)
        p1 = col1.selectbox(t("Joueur 1", "Player 1"), options=players_ranked, index=0, key="comp_p1")
        p2 = col2.selectbox(t("Joueur 2", "Player 2"), options=players_ranked, index=1, key="comp_p2")
        if p1 == p2:
            st.warning(t("Choisis deux joueurs différents.", "Pick two different players."))
        else:
            try:
                comp_table = compare_players(shots_all, p1, p2)
                comp_table["métrique"] = [t(*METRIC_NAMES.get(m, (m, m))) for m in comp_table["métrique"]]
                comp_table = comp_table.rename(columns={"métrique": t("Indicateur", "Metric")})
                st.dataframe(comp_table, width="stretch", hide_index=True)
                col_a, col_b = st.columns(2)
                with col_a:
                    show(shot_map(filter_shots(shots_all, player=p1), title=p1))
                with col_b:
                    show(shot_map(filter_shots(shots_all, player=p2), title=p2))
            except ValueError as e:
                st.error(str(e))

footer("Données : StatsBomb (Open Data)", "Data: StatsBomb (Open Data)")
