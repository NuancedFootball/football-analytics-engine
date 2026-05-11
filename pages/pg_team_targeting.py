import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import pathlib

st.title("Team Gap Analysis + Player Fit Recommender")
st.caption("Select a team. Diagnose ecosystem gaps. Get ranked transfer targets that fit.")

SD = pathlib.Path("scraped_data")

# ── Load all data ──────────────────────────────────────────────
@st.cache_data
def load_all():
    d = {}
    files = {
        "cpa": "engine_cpa_profiles.csv",
        "eco": "engine_team_ecosystems_v3.csv",
        "adv": "engine_adversity.csv",
        "ti":  "engine_transfer_intel.csv",
        "sim": "engine_similarity.csv",
        "cent":"engine_archetype_centroids.csv",
    }
    for key, fname in files.items():
        p = SD / fname
        d[key] = pd.read_csv(p) if p.exists() else None
    return d

data = load_all()
cpa = data["cpa"]
eco = data["eco"]
adv = data["adv"]
ti  = data["ti"]
sim = data["sim"]
cent = data["cent"]

if cpa is None or eco is None:
    st.error("CPA profiles and team ecosystems required. Run build_engine_core.py.")
    st.stop()

# ── Team selector ──────────────────────────────────────────────
teams = sorted(eco["team"].unique().tolist())
sel_team = st.selectbox("Select Team", teams, key="tgt_team")

team_eco = eco[eco["team"] == sel_team].iloc[0]
team_league = team_eco["league"]
team_players = cpa[cpa["team"] == sel_team].copy()
team_outfield = team_players[~team_players["position"].str.contains("GK", case=False, na=False)]

st.divider()

# ══════════════════════════════════════════════════════════════
# SECTION 1: TEAM ECOSYSTEM SNAPSHOT
# ══════════════════════════════════════════════════════════════
st.header("1. Ecosystem Snapshot")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("xGD", round(team_eco["xGD"], 2))
c2.metric("PPG", round(team_eco["ppg"], 2))
c3.metric("Squad Size", int(team_eco["players"]))
c4.metric("Goal Conc.", round(team_eco["goal_concentration"], 3))
c5.metric("Archetypes", int(team_eco["n_archetypes"]))

# League rank context
league_teams = eco[eco["league"] == team_league].sort_values("xGD", ascending=False).reset_index(drop=True)
league_rank = league_teams[league_teams["team"] == sel_team].index[0] + 1
league_size = len(league_teams)
st.caption(sel_team + " ranks #" + str(league_rank) + " of " + str(league_size) + " in " + team_league + " by xGD")

# ══════════════════════════════════════════════════════════════
# SECTION 2: ARCHETYPE COMPOSITION ANALYSIS
# ══════════════════════════════════════════════════════════════
st.header("2. Archetype Composition")

if "archetype" in team_outfield.columns:
    # Team archetype distribution
    team_arch = team_outfield["archetype"].value_counts().reset_index()
    team_arch.columns = ["archetype", "count"]

    # League leaders archetype distribution (top 3 by xGD)
    top3_teams = league_teams.head(3)["team"].tolist()
    top3_players = cpa[(cpa["team"].isin(top3_teams)) & (cpa["league"] == team_league)]
    top3_outfield = top3_players[~top3_players["position"].str.contains("GK", case=False, na=False)]
    top3_arch = top3_outfield["archetype"].value_counts(normalize=True).reset_index()
    top3_arch.columns = ["archetype", "top3_pct"]

    team_arch_pct = team_outfield["archetype"].value_counts(normalize=True).reset_index()
    team_arch_pct.columns = ["archetype", "team_pct"]

    # Merge for comparison
    arch_comp = pd.merge(team_arch_pct, top3_arch, on="archetype", how="outer").fillna(0)
    arch_comp["gap"] = arch_comp["top3_pct"] - arch_comp["team_pct"]
    arch_comp = arch_comp.sort_values("gap", ascending=False)

    col1, col2 = st.columns(2)
    with col1:
        fig_team = px.pie(team_arch, values="count", names="archetype",
                          title=sel_team + " Archetype Mix")
        fig_team.update_layout(height=350)
        st.plotly_chart(fig_team, use_container_width=True)
    with col2:
        fig_comp = px.bar(arch_comp, x="archetype", y=["team_pct","top3_pct"],
                          barmode="group",
                          title="vs Top 3 " + team_league + " Teams",
                          labels={"value":"Proportion","variable":"Source"})
        fig_comp.update_layout(height=350)
        st.plotly_chart(fig_comp, use_container_width=True)

    # Identify gaps
    underrep = arch_comp[arch_comp["gap"] > 0.05]
    if len(underrep) > 0:
        gap_archs = underrep["archetype"].tolist()
        gap_str = ", ".join(gap_archs)
        st.warning("Archetype gap detected: " + sel_team + " is underweight in **" + gap_str + "** compared to league leaders.")
    else:
        gap_archs = []
        st.success("Archetype composition is well-balanced relative to league leaders.")
else:
    gap_archs = []

# ══════════════════════════════════════════════════════════════
# SECTION 3: OUTPUT DEPENDENCY RISK
# ══════════════════════════════════════════════════════════════
st.header("3. Output Dependency Risk")

team_out_sorted = team_outfield.sort_values("cpa_xGI_p90", ascending=False)
if len(team_out_sorted) > 0:
    top_player = team_out_sorted.iloc[0]
    team_total_xgi = team_outfield["cpa_xGI_p90"].sum()
    if team_total_xgi > 0:
        top_share = top_player["cpa_xGI_p90"] / team_total_xgi
    else:
        top_share = 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Top Contributor", top_player["player"])
    c2.metric("CPA xGI/90", round(top_player["cpa_xGI_p90"], 3))
    c3.metric("Share of Team xGI", str(round(top_share * 100, 1)) + "%")

    # Dependency chart
    chart_data = team_out_sorted.head(10)[["player","cpa_xGI_p90"]].copy()
    fig_dep = px.bar(chart_data, x="player", y="cpa_xGI_p90",
                     title="Top 10 Contributors by CPA xGI/90",
                     color="cpa_xGI_p90", color_continuous_scale="OrRd")
    fig_dep.update_layout(height=400, showlegend=False)
    st.plotly_chart(fig_dep, use_container_width=True)

    # Concentration warning
    if top_share > 0.25:
        st.warning("High dependency risk: " + top_player["player"] + " accounts for " + str(round(top_share*100,1)) + "% of team CPA xGI output.")
    elif top_share > 0.18:
        st.info("Moderate concentration: " + top_player["player"] + " carries " + str(round(top_share*100,1)) + "% of output.")
    else:
        st.success("Output is well-distributed across the squad.")

# ══════════════════════════════════════════════════════════════
# SECTION 4: RESILIENCE & BIG-GAME PROFILE
# ══════════════════════════════════════════════════════════════
st.header("4. Squad Resilience Profile")

res_col = "resilience_ratio"
bg_col = "big_game_ratio"

if res_col in team_outfield.columns and bg_col in team_outfield.columns:
    team_avg_res = team_outfield[res_col].mean()
    team_avg_bg = team_outfield[bg_col].mean()
    league_avg_res = cpa[cpa["league"] == team_league][res_col].mean()
    league_avg_bg = cpa[cpa["league"] == team_league][bg_col].mean()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Squad Avg Resilience", round(team_avg_res, 3),
              delta=round(team_avg_res - league_avg_res, 3))
    c2.metric("League Avg Resilience", round(league_avg_res, 3))
    c3.metric("Squad Avg Big-Game", round(team_avg_bg, 3),
              delta=round(team_avg_bg - league_avg_bg, 3))
    c4.metric("League Avg Big-Game", round(league_avg_bg, 3))

    # Players with poor resilience
    weak_res = team_outfield[team_outfield[res_col] < league_avg_res * 0.8]
    if len(weak_res) > 0:
        st.caption("Players below 80% of league avg resilience:")
        show = ["player","position","archetype",res_col,bg_col,"cpa_xGI_p90","total_minutes"]
        show = [c for c in show if c in weak_res.columns]
        st.dataframe(weak_res[show].sort_values(res_col).reset_index(drop=True),
                     use_container_width=True)

# ══════════════════════════════════════════════════════════════
# SECTION 5: POSITIONAL xG PROFILE
# ══════════════════════════════════════════════════════════════
st.header("5. Shot Profile Analysis")

shot_cols = ["pct_6yd","pct_pen","pct_outside"]
if all(c in team_outfield.columns for c in shot_cols):
    team_shot = team_outfield[shot_cols].mean()
    league_shot = cpa[cpa["league"] == team_league][shot_cols].mean()

    shot_comp = pd.DataFrame({
        "Zone": ["6-Yard Box","Penalty Area","Outside Box"],
        sel_team: [team_shot["pct_6yd"], team_shot["pct_pen"], team_shot["pct_outside"]],
        "League Avg": [league_shot["pct_6yd"], league_shot["pct_pen"], league_shot["pct_outside"]],
    })
    fig_shot = px.bar(shot_comp, x="Zone", y=[sel_team, "League Avg"],
                      barmode="group", title="Shot Zone Distribution vs League Average")
    fig_shot.update_layout(height=400)
    st.plotly_chart(fig_shot, use_container_width=True)

# ══════════════════════════════════════════════════════════════
# SECTION 6: PLAYER FIT RECOMMENDATIONS
# ══════════════════════════════════════════════════════════════
st.header("6. Player Fit Recommendations")
st.caption("Players from other teams ranked by ecosystem fit score")

# Build candidate pool: all players NOT on this team
candidates = cpa[cpa["team"] != sel_team].copy()
candidates = candidates[~candidates["position"].str.contains("GK", case=False, na=False)]
candidates = candidates[candidates["total_minutes"] >= 900]

# Merge adversity data
if adv is not None and "player_id" in adv.columns and "player_id" in candidates.columns:
    adv_cols = ["player_id","adversity_score","adversity_rank"]
    adv_cols = [c for c in adv_cols if c in adv.columns]
    candidates = candidates.merge(adv[adv_cols], on="player_id", how="left")

# Merge transfer intel
if ti is not None and "player_id" in ti.columns and "player_id" in candidates.columns:
    ti_cols = ["player_id","transfer_score","transfer_rank","output_efficiency","growth_signal"]
    ti_cols = [c for c in ti_cols if c in ti.columns]
    ti_merge = [c for c in ti_cols if c not in candidates.columns]
    if "player_id" in ti_merge:
        ti_merge = ti_cols
    else:
        ti_merge = ["player_id"] + ti_merge
    candidates = candidates.merge(ti[ti_merge], on="player_id", how="left")

# ── Compute Fit Score ──────────────────────────────────────────
# Components:
# 1. Archetype Need (0-30): bonus if player fills an underrepresented archetype
# 2. Output Quality (0-25): CPA xGI/90 percentile
# 3. Resilience Fit (0-20): resilience + big-game above team avg
# 4. Role Burden Complement (0-15): RBI signals capacity to carry load
# 5. Transfer Feasibility (0-10): from transfer_score

fit_scores = []

for idx, row in candidates.iterrows():
    score = 0.0

    # 1. Archetype need (0-30)
    if len(gap_archs) > 0 and "archetype" in row.index:
        if row.get("archetype","") in gap_archs:
            score += 30.0
        else:
            score += 5.0
    else:
        score += 15.0  # neutral if no gap detected

    # 2. Output quality (0-25)
    xgi = row.get("cpa_xGI_p90", 0)
    if xgi > 0:
        xgi_pctl = (candidates["cpa_xGI_p90"] <= xgi).mean()
        score += xgi_pctl * 25.0

    # 3. Resilience fit (0-20)
    p_res = row.get("resilience_ratio", 0)
    p_bg = row.get("big_game_ratio", 0)
    if team_outfield[res_col].mean() > 0:
        res_bonus = min(p_res / max(team_outfield[res_col].mean(), 0.001), 2.0)
        bg_bonus = min(p_bg / max(team_outfield[bg_col].mean(), 0.001), 2.0)
        score += ((res_bonus + bg_bonus) / 4.0) * 20.0

    # 4. Role burden complement (0-15)
    p_rbi = row.get("role_burden", 0)
    team_avg_rbi = team_outfield["role_burden"].mean() if "role_burden" in team_outfield.columns else 0
    if p_rbi > team_avg_rbi:
        rbi_bonus = min((p_rbi - team_avg_rbi) / max(team_avg_rbi, 0.001), 2.0)
        score += min(rbi_bonus * 7.5, 15.0)
    else:
        score += 5.0

    # 5. Transfer feasibility (0-10)
    ts = row.get("transfer_score", 0)
    if ts > 0 and "transfer_score" in candidates.columns:
        ts_pctl = (candidates["transfer_score"].dropna() <= ts).mean()
        score += ts_pctl * 10.0

    fit_scores.append(round(score, 2))

candidates["fit_score"] = fit_scores

# ── Filter controls ────────────────────────────────────────────
with st.sidebar:
    st.subheader("Recommendation Filters")

    if "archetype" in candidates.columns:
        filter_archs = st.multiselect(
            "Archetype Filter",
            sorted(candidates["archetype"].dropna().unique().tolist()),
            default=gap_archs if gap_archs else sorted(candidates["archetype"].dropna().unique().tolist()),
            key="tgt_archs"
        )
    else:
        filter_archs = None

    filter_leagues = st.multiselect(
        "Source Leagues",
        sorted(candidates["league"].unique().tolist()),
        default=sorted(candidates["league"].unique().tolist()),
        key="tgt_leagues"
    )

    min_xgi = st.slider("Min CPA xGI/90", 0.0, 1.0, 0.0, step=0.05, key="tgt_xgi")
    max_results = st.slider("Max Results", 10, 100, 30, step=5, key="tgt_max")

rec = candidates.copy()
if filter_archs and "archetype" in rec.columns:
    rec = rec[rec["archetype"].isin(filter_archs)]
if filter_leagues:
    rec = rec[rec["league"].isin(filter_leagues)]
rec = rec[rec["cpa_xGI_p90"] >= min_xgi]
rec = rec.nlargest(max_results, "fit_score")

# ── Results table ──────────────────────────────────────────────
st.subheader("Top " + str(len(rec)) + " Recommended Players for " + sel_team)

show_cols = ["player","team","league","position","archetype","fit_score",
             "cpa_xGI_p90","cpa_xG_p90","cpa_xA_p90","role_burden",
             "resilience_ratio","big_game_ratio","total_minutes","matches"]
if "transfer_score" in rec.columns:
    show_cols.insert(6, "transfer_score")
if "output_efficiency" in rec.columns:
    show_cols.insert(7, "output_efficiency")
show_cols = [c for c in show_cols if c in rec.columns]

display = rec[show_cols].reset_index(drop=True)
display.index = display.index + 1
st.dataframe(display, use_container_width=True, height=600)

# ── Fit Score Scatter ──────────────────────────────────────────
if len(rec) > 1:
    st.subheader("Recommendation Map")
    color_c = "archetype" if "archetype" in rec.columns else "league"
    fig_rec = px.scatter(
        rec, x="cpa_xGI_p90", y="fit_score",
        hover_name="player", color=color_c,
        size="total_minutes", size_max=15, opacity=0.8,
        title="Fit Score vs Output: Recommendations for " + sel_team
    )
    fig_rec.update_layout(height=550)
    st.plotly_chart(fig_rec, use_container_width=True)

# ── Deep Dive: Compare Recommendation to Squad ────────────────
st.divider()
st.subheader("Deep Dive: Compare a Recommendation to Current Squad")

if len(rec) > 0:
    rec_player = st.selectbox("Select Recommended Player",
                              rec["player"].tolist(), key="tgt_deep")
    rec_row = rec[rec["player"] == rec_player].iloc[0]

    # Radar: recommended player percentiles vs team average percentiles
    radar_cols = ["cpa_xG_p90","cpa_xA_p90","cpa_xGChain_p90","cpa_xGBuildup_p90",
                  "role_burden","shots_p90","key_passes_p90"]
    radar_cols = [c for c in radar_cols if c in cpa.columns]

    if radar_cols:
        labels = [c.replace("cpa_","").replace("_p90","").replace("_"," ").title()
                  for c in radar_cols]

        # Recommended player percentiles (vs all players)
        rec_vals = [(cpa[c] <= rec_row[c]).mean() * 100 for c in radar_cols]

        # Team average percentiles
        team_means = team_outfield[radar_cols].mean()
        team_vals = [(cpa[c] <= team_means[c]).mean() * 100 for c in radar_cols]

        fig_deep = go.Figure()
        fig_deep.add_trace(go.Scatterpolar(
            r=rec_vals + [rec_vals[0]],
            theta=labels + [labels[0]],
            fill="toself", name=rec_player,
            line_color="#FF6B35"
        ))
        fig_deep.add_trace(go.Scatterpolar(
            r=team_vals + [team_vals[0]],
            theta=labels + [labels[0]],
            fill="toself", name=sel_team + " Avg",
            line_color="#4ECDC4"
        ))
        fig_deep.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            title=rec_player + " vs " + sel_team + " Squad Average",
            height=500
        )
        st.plotly_chart(fig_deep, use_container_width=True)

    # Key stats comparison
    c1, c2, c3 = st.columns(3)
    c1.metric(rec_player + " xGI/90",
              round(rec_row.get("cpa_xGI_p90", 0), 3))
    team_best_xgi = team_outfield["cpa_xGI_p90"].max() if len(team_outfield) > 0 else 0
    c2.metric("Current Best xGI/90",
              round(team_best_xgi, 3))
    c3.metric("Fit Score", round(rec_row.get("fit_score", 0), 1))

    # Why this player fits
    st.caption("Fit Breakdown:")
    reasons = []
    if len(gap_archs) > 0 and rec_row.get("archetype","") in gap_archs:
        reasons.append("Fills archetype gap (" + rec_row["archetype"] + ")")
    if rec_row.get("cpa_xGI_p90", 0) > team_best_xgi:
        reasons.append("Would be the top CPA xGI contributor on the team")
    if rec_row.get("resilience_ratio", 0) > team_outfield[res_col].mean():
        reasons.append("Above-average resilience for this squad")
    if rec_row.get("big_game_ratio", 0) > team_outfield[bg_col].mean():
        reasons.append("Strong big-game performer relative to squad")
    if rec_row.get("role_burden", 0) > team_outfield["role_burden"].mean():
        reasons.append("Higher role burden capacity than squad average")
    if not reasons:
        reasons.append("Balanced profile that complements existing squad")
    for r in reasons:
        st.write("- " + r)

# ── Export ─────────────────────────────────────────────────────
st.divider()
if len(rec) > 0:
    csv = display.to_csv(index=False)
    fname = sel_team.lower().replace(" ","_") + "_recommendations.csv"
    st.download_button("Download Recommendations CSV", csv, fname, "text/csv")
