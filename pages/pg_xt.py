import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

st.title("Expected Threat (xT) Surfaces")
D = "scraped_data"

@st.cache_data
def load_league():
    return pd.read_csv(f"{D}/engine_xt_league.csv")

@st.cache_data
def load_team():
    return pd.read_csv(f"{D}/engine_xt_team.csv")

xt_lg = load_league()
xt_tm = load_team()

st.header("League xT Heatmaps")
entity = st.selectbox("Select", sorted(xt_lg["entity"].unique()))
sub = xt_lg[xt_lg["entity"]==entity]

grid = np.zeros((16, 12))
for _, r in sub.iterrows():
    grid[int(r["cell_x"]), int(r["cell_y"])] = r["xT"]

fig = px.imshow(grid.T, origin="lower", color_continuous_scale="YlOrRd",
                labels=dict(x="Pitch Length (own goal → opp goal)", y="Pitch Width", color="xT"),
                title=f"xT Surface: {entity}", height=400, aspect="auto")
st.plotly_chart(fig, use_container_width=True)

st.header("Team xT Comparison")
teams = sorted(xt_tm["entity"].unique())
c1, c2 = st.columns(2)
with c1:
    t1 = st.selectbox("Team A", teams, index=0)
with c2:
    t2 = st.selectbox("Team B", teams, index=min(1, len(teams)-1))

col1, col2 = st.columns(2)
for col, t in zip([col1, col2], [t1, t2]):
    sub = xt_tm[xt_tm["entity"]==t]
    grid = np.zeros((16, 12))
    for _, r in sub.iterrows():
        grid[int(r["cell_x"]), int(r["cell_y"])] = r["xT"]
    fig = px.imshow(grid.T, origin="lower", color_continuous_scale="YlOrRd",
                    title=t, height=350, aspect="auto")
    col.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.caption("xT computed using Karun Singh's iterative framework (5 iterations) on 40,757 shots.")
