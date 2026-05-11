import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.title("Expected Threat (xT) Surfaces")
D = "scraped_data"

@st.cache_data
def load_xt_league():
    return pd.read_csv("{}/engine_xt_league.csv".format(D))

@st.cache_data
def load_xt_team():
    return pd.read_csv("{}/engine_xt_team.csv".format(D))

xt_lg = load_xt_league()
xt_tm = load_xt_team()

tab1, tab2 = st.tabs(["League xT", "Team xT"])

def plot_xt_heatmap(df_subset, title):
    pivot = df_subset.pivot(index="cell_y", columns="cell_x", values="xT")
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=["X{}".format(i) for i in pivot.columns],
        y=["Y{}".format(j) for j in pivot.index],
        colorscale="YlOrRd",
        colorbar=dict(title="xT"),
    ))
    fig.update_layout(
        title=title, height=400, width=700,
        xaxis_title="Pitch Length (own goal to opponent goal)",
        yaxis_title="Pitch Width",
        yaxis=dict(autorange="reversed"),
    )
    return fig

with tab1:
    entities = sorted(xt_lg["entity"].unique())
    idx = entities.index("GLOBAL") if "GLOBAL" in entities else 0
    sel = st.selectbox("Select League / Global", entities, index=idx)
    subset = xt_lg[xt_lg["entity"] == sel]
    st.plotly_chart(plot_xt_heatmap(subset, "xT Surface: {}".format(sel)), use_container_width=True)
    col1, col2 = st.columns(2)
    col1.metric("Max xT", "{:.4f}".format(subset["xT"].max()))
    col2.metric("Mean xT", "{:.6f}".format(subset["xT"].mean()))

with tab2:
    teams = sorted(xt_tm["entity"].unique())
    sel_tm = st.selectbox("Select Team", teams)
    subset_tm = xt_tm[xt_tm["entity"] == sel_tm]
    st.plotly_chart(plot_xt_heatmap(subset_tm, "xT Surface: {}".format(sel_tm)), use_container_width=True)
    st.markdown("Top 5 Threat Zones:")
    for _, r in subset_tm.nlargest(5, "xT").iterrows():
        st.write("Zone ({}, {}): xT = {:.4f}".format(int(r["cell_x"]), int(r["cell_y"]), r["xT"]))
