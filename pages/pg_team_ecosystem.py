
import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.title("\U0001f3df\ufe0f Team Ecosystems")

eco_path = "scraped_data/engine_team_ecosystems_v2.csv"
dep_path = "scraped_data/engine_team_dependencies.csv"

if not os.path.exists(eco_path):
    st.error("Run `python integrate_gk_engine.py` first.")
    st.stop()

eco = pd.read_csv(eco_path)
dep = pd.read_csv(dep_path) if os.path.exists(dep_path) else None

for col in eco.columns:
    if col not in ["team", "league", "primary_gk_name", "primary_gk_id", "gk_best_zone"]:
        eco[col] = pd.to_numeric(eco[col], errors="coerce")

# Filter out rows with no GK data (composite team names from outfield data)
eco_with_gk = eco.dropna(subset=["primary_gk_name"]) if "primary_gk_name" in eco.columns else eco

leagues = ["All"] + sorted(eco_with_gk["league"].dropna().unique().tolist())
selected_league = st.selectbox("League", leagues)
filtered = eco_with_gk if selected_league == "All" else eco_with_gk[eco_with_gk["league"] == selected_league]

st.markdown("### Team Defensive Identity (Primary GK)")
gk_cols = ["team", "league", "primary_gk_name", "gk_save_pct", "gk_goals_prevented_per90",
            "gk_adversity_index", "gk_ha_save_delta", "gk_consistency_cv", "gk_depth"]
avail = [c for c in gk_cols if c in filtered.columns]
st.dataframe(filtered[avail].sort_values(
    "gk_goals_prevented_per90" if "gk_goals_prevented_per90" in filtered.columns else avail[-1],
    ascending=False
).head(30), width="stretch", hide_index=True)

# Scatter: GK Save % vs Team xGA — handle NaN safely
if "gk_save_pct" in filtered.columns and "gk_xGA" in filtered.columns:
    scatter_df = filtered.dropna(subset=["gk_save_pct", "gk_xGA"]).copy()
    if len(scatter_df) > 0:
        st.markdown("### GK Save % vs Total xGA Faced")
        # Use size only if column exists and has no NaN
        size_col = None
        if "gk_goals_prevented_per90" in scatter_df.columns:
            scatter_df["_size"] = scatter_df["gk_goals_prevented_per90"].fillna(0).clip(lower=0)
            if scatter_df["_size"].sum() > 0:
                size_col = "_size"

        fig = px.scatter(scatter_df, x="gk_xGA", y="gk_save_pct",
                          color="league", hover_name="team",
                          hover_data=["primary_gk_name"],
                          size=size_col,
                          labels={"gk_xGA": "Total xGA (season)", "gk_save_pct": "Save %"})
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)

# Dependencies
if dep is not None:
    st.markdown("### Cross-Positional Dependencies")
    for col in dep.columns:
        if col not in ["team", "league"]:
            dep[col] = pd.to_numeric(dep[col], errors="coerce")

    dep_filtered = dep if selected_league == "All" else dep[dep["league"] == selected_league]

    dep_cols = ["team", "league", "def_buildup_share", "fwd_xG_share",
                "corr_gp_vs_DEF_buildup", "corr_save_pct_vs_team_xG",
                "def_buildup_cleansheet_vs_not"]
    avail_dep = [c for c in dep_cols if c in dep_filtered.columns]
    st.dataframe(dep_filtered[avail_dep].sort_values(
        avail_dep[-1] if avail_dep else "team", ascending=False
    ).head(30), width="stretch", hide_index=True)

    if "def_buildup_share" in dep_filtered.columns and "fwd_xG_share" in dep_filtered.columns:
        st.markdown("### Defensive Buildup Share vs Forward xG Share")
        fig2 = px.scatter(dep_filtered.dropna(subset=["def_buildup_share", "fwd_xG_share"]),
                           x="def_buildup_share", y="fwd_xG_share",
                           color="league", hover_name="team",
                           labels={"def_buildup_share": "DEF Buildup Share %",
                                   "fwd_xG_share": "FWD xG Share %"})
        fig2.update_layout(height=450)
        st.plotly_chart(fig2, use_container_width=True)
