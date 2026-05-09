
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import os

st.title("\U0001f9e4 Goalkeeper Profiles")

if not os.path.exists("scraped_data/engine_gk_profiles.csv"):
    st.error("Run `python integrate_gk_engine.py` first.")
    st.stop()

gk = pd.read_csv("scraped_data/engine_gk_profiles.csv")
gk_sim = pd.read_csv("scraped_data/engine_gk_similarity.csv") if os.path.exists("scraped_data/engine_gk_similarity.csv") else None

for col in gk.columns:
    if col not in ["gk_player_id", "gk_name", "gk_team", "league", "best_zone"]:
        gk[col] = pd.to_numeric(gk[col], errors="coerce")

# ── Filters ──────────────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)
leagues = ["All"] + sorted(gk["league"].unique().tolist())
selected_league = col1.selectbox("League", leagues)
min_matches = col2.slider("Min Matches", 10, 38, 15)
sort_by = col3.selectbox("Sort By", ["goals_prevented_pm", "save_pct", "adversity_index",
                                       "ha_save_delta", "consistency_cv", "clean_sheet_pct"])

filtered = gk[gk["matches"] >= min_matches]
if selected_league != "All":
    filtered = filtered[filtered["league"] == selected_league]

filtered = filtered.sort_values(sort_by, ascending=False, na_position="last")

# ── Leaderboard ──────────────────────────────────────────────────────
st.markdown("### Leaderboard")
display_cols = ["gk_name", "gk_team", "league", "matches", "save_pct",
                "goals_prevented_pm", "adversity_index", "ha_save_delta",
                "consistency_cv", "clean_sheet_pct", "best_zone"]
st.dataframe(filtered[display_cols].head(30), use_container_width=True, hide_index=True)

# ── Scatter Plot ─────────────────────────────────────────────────────
st.markdown("### Save % vs Goals Prevented per Match")
fig_scatter = px.scatter(
    filtered, x="save_pct", y="goals_prevented_pm",
    color="league", size="matches", hover_name="gk_name",
    hover_data=["gk_team", "adversity_index"],
    labels={"save_pct": "Save %", "goals_prevented_pm": "Goals Prevented / Match"},
)
fig_scatter.update_layout(height=500)
st.plotly_chart(fig_scatter, use_container_width=True)

# ── Individual Radar ─────────────────────────────────────────────────
st.markdown("### GK Radar Profile")
selected_gk = st.selectbox("Select Goalkeeper", filtered["gk_name"].tolist())
if selected_gk:
    row = filtered[filtered["gk_name"] == selected_gk].iloc[0]

    radar_metrics = {
        "Save %":           row.get("save_pct", 0) or 0,
        "Goals Prev/M":     max((row.get("goals_prevented_pm", 0) or 0) * 100, 0),
        "Clean Sheet %":    row.get("clean_sheet_pct", 0) or 0,
        "Home Save %":      row.get("home_save_pct", 0) or 0,
        "Away Save %":      row.get("away_save_pct", 0) or 0,
        "vs Hard Save %":   row.get("vs_hard_save_pct", 0) or 0,
        "Loss Resilience":  row.get("loss_resilience", 0) or 0,
    }

    categories = list(radar_metrics.keys())
    values = list(radar_metrics.values())

    fig_radar = go.Figure(data=go.Scatterpolar(
        r=values + [values[0]],
        theta=categories + [categories[0]],
        fill="toself",
        name=selected_gk,
        line=dict(color="#1f77b4"),
    ))
    fig_radar.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=False, height=450,
        title=f"{selected_gk} ({row['gk_team']}, {row['league']})"
    )
    st.plotly_chart(fig_radar, use_container_width=True)

    # Show similar GKs
    if gk_sim is not None:
        sim_row = gk_sim[gk_sim["gk_name"] == selected_gk]
        if len(sim_row) > 0:
            st.markdown("**Most Similar Goalkeepers:**")
            sim_row = sim_row.iloc[0]
            sim_data = []
            for r in range(1, 6):
                sim_data.append({
                    "Rank": r,
                    "Name": sim_row.get(f"sim_{r}_name", ""),
                    "Team": sim_row.get(f"sim_{r}_team", ""),
                    "League": sim_row.get(f"sim_{r}_league", ""),
                    "Similarity": sim_row.get(f"sim_{r}_score", ""),
                })
            st.dataframe(pd.DataFrame(sim_data), use_container_width=True, hide_index=True)

# ── Zone Breakdown Bar Chart ─────────────────────────────────────────
st.markdown("### Zone Performance: Goals Prevented by Zone")
zone_data = filtered[["gk_name", "zone_gp_six_yard", "zone_gp_pen_area", "zone_gp_outside_box"]].head(15)
zone_melted = zone_data.melt(id_vars="gk_name", var_name="Zone", value_name="Goals Prevented")
zone_melted["Zone"] = zone_melted["Zone"].map({
    "zone_gp_six_yard": "Six-Yard Box",
    "zone_gp_pen_area": "Penalty Area",
    "zone_gp_outside_box": "Outside Box",
})
fig_zone = px.bar(zone_melted, x="gk_name", y="Goals Prevented", color="Zone",
                   barmode="group", labels={"gk_name": ""})
fig_zone.update_layout(height=400, xaxis_tickangle=-45)
st.plotly_chart(fig_zone, use_container_width=True)
