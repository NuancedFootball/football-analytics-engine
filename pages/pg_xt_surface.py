import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import pathlib
from glossary import show_glossary

st.title("Expected Threat (xT) Surfaces")
st.caption("Pitch grid | Iterative value computation from shot-level data")
show_glossary()

SD = pathlib.Path("scraped_data")

@st.cache_data
def load_xt():
    lp = SD / "engine_xt_league.csv"
    tp = SD / "engine_xt_team.csv"
    return (pd.read_csv(lp) if lp.exists() else None,
            pd.read_csv(tp) if tp.exists() else None)

league_df, team_df = load_xt()
if league_df is None:
    st.error("xT data not found.")
    st.stop()

def extract_grid(sub):
    val_cols = [c for c in sub.columns if c.startswith("col_")]
    if val_cols:
        return sub[val_cols].values
    numeric = sub.select_dtypes(include=[np.number]).columns.tolist()
    non_meta = [c for c in numeric if c not in ["row","league"]]
    return sub[non_meta].values if non_meta else np.zeros((12,16))

tab1, tab2 = st.tabs(["League xT", "Team xT"])
with tab1:
    opts = sorted(league_df["league"].unique().tolist()) if "league" in league_df.columns else ["GLOBAL"]
    sel = st.selectbox("League", opts, key="xt_l")
    sub = league_df[league_df["league"]==sel] if "league" in league_df.columns else league_df
    grid = extract_grid(sub)
    fig = go.Figure(data=go.Heatmap(z=grid, colorscale="YlOrRd", colorbar=dict(title="xT")))
    fig.update_layout(title="xT: " + sel, xaxis_title="Width", yaxis_title="Length",
                      height=500, yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig, use_container_width=True)
    c1,c2 = st.columns(2)
    c1.metric("Max xT", round(float(grid.max()),4))
    c2.metric("Mean xT", round(float(grid.mean()),6))

with tab2:
    if team_df is not None and len(team_df) > 0:
        tcol = "team" if "team" in team_df.columns else team_df.columns[0]
        sel_t = st.selectbox("Team", sorted(team_df[tcol].unique().tolist()), key="xt_t")
        tsub = team_df[team_df[tcol]==sel_t]
        tgrid = extract_grid(tsub)
        fig2 = go.Figure(data=go.Heatmap(z=tgrid, colorscale="YlOrRd", colorbar=dict(title="xT")))
        fig2.update_layout(title="xT: " + sel_t, height=500, yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig2, use_container_width=True)
