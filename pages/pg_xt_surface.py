import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import pathlib

st.title("Expected Threat (xT) Surfaces")
st.caption("Pitch grid | Iterative value computation from shot-level data")

SD = pathlib.Path("scraped_data")

@st.cache_data
def load_xt():
    lp = SD / "engine_xt_league.csv"
    tp = SD / "engine_xt_team.csv"
    league_df = pd.read_csv(lp) if lp.exists() else None
    team_df = pd.read_csv(tp) if tp.exists() else None
    return league_df, team_df

league_df, team_df = load_xt()

if league_df is None:
    st.error("engine_xt_league.csv not found. Run build_engine_core.py first.")
    st.stop()

def extract_grid(sub):
    val_cols = [c for c in sub.columns if c.startswith("col_")]
    if val_cols:
        return sub[val_cols].values
    numeric = sub.select_dtypes(include=[np.number]).columns.tolist()
    non_meta = [c for c in numeric if c not in ["row","league"]]
    if non_meta:
        return sub[non_meta].values
    return np.zeros((12, 16))

tab1, tab2 = st.tabs(["League xT", "Team xT"])

with tab1:
    if "league" in league_df.columns:
        options = sorted(league_df["league"].unique().tolist())
    else:
        options = ["GLOBAL"]
    sel = st.selectbox("League", options, key="xt_l")
    if "league" in league_df.columns:
        sub = league_df[league_df["league"] == sel]
    else:
        sub = league_df
    grid = extract_grid(sub)
    fig = go.Figure(data=go.Heatmap(z=grid, colorscale="YlOrRd",
                                     colorbar=dict(title="xT")))
    fig.update_layout(title="xT Surface: " + sel,
                      xaxis_title="Width", yaxis_title="Length",
                      height=500, yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig, use_container_width=True)
    c1, c2 = st.columns(2)
    c1.metric("Max xT", round(float(grid.max()), 4))
    c2.metric("Mean xT", round(float(grid.mean()), 6))

with tab2:
    if team_df is not None and len(team_df) > 0:
        tcol = "team" if "team" in team_df.columns else team_df.columns[0]
        teams = sorted(team_df[tcol].unique().tolist())
        sel_t = st.selectbox("Team", teams, key="xt_t")
        tsub = team_df[team_df[tcol] == sel_t]
        tgrid = extract_grid(tsub)
        fig2 = go.Figure(data=go.Heatmap(z=tgrid, colorscale="YlOrRd",
                                          colorbar=dict(title="xT")))
        fig2.update_layout(title="xT: " + sel_t, xaxis_title="Width",
                           yaxis_title="Length", height=500,
                           yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Team xT data not available.")
