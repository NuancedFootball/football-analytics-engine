import streamlit as st
import pandas as pd
import plotly.express as px
import pathlib
from glossary import show_glossary, sidebar_filters

st.title("Player Archetype Explorer")
st.caption("PCA + K-Means | Filter by position, age, minutes, league, value")

SD = pathlib.Path("scraped_data")

@st.cache_data
def load():
    cp = SD / "engine_cpa_profiles.csv"
    return pd.read_csv(cp) if cp.exists() else None

cpa = load()
if cpa is None:
    st.error("CPA profiles not found.")
    st.stop()

show_glossary()

# Filter out GKs from display
if "position_band" in cpa.columns:
    outfield = cpa[cpa["position_band"] != "Goalkeeper"].copy()
else:
    outfield = cpa.copy()

fdf = sidebar_filters(outfield, prefix="at")

st.subheader("Archetype Distribution (" + str(len(fdf)) + " players)")
if "archetype" in fdf.columns:
    dist = fdf["archetype"].value_counts().reset_index()
    dist.columns = ["archetype","count"]
    fig_d = px.bar(dist, x="archetype", y="count", color="archetype",
                   title="Filtered Archetype Counts")
    fig_d.update_layout(showlegend=False, height=350)
    st.plotly_chart(fig_d, use_container_width=True)

# Cross-tab: Archetype x Position Band
if "archetype" in fdf.columns and "position_band" in fdf.columns:
    st.subheader("Archetype by Position Band")
    ct = pd.crosstab(fdf["archetype"], fdf["position_band"])
    st.dataframe(ct, use_container_width=True)

# PCA scatter
pca_cols = [c for c in fdf.columns if c.startswith("pca_")]
if len(pca_cols) >= 2 and "archetype" in fdf.columns:
    st.subheader("PCA Projection (colored by archetype)")
    fig_p = px.scatter(fdf, x=pca_cols[0], y=pca_cols[1],
                       color="archetype", hover_name="player",
                       symbol="position_band" if "position_band" in fdf.columns else None,
                       opacity=0.6, title="Clusters in PCA Space")
    fig_p.update_layout(height=600)
    st.plotly_chart(fig_p, use_container_width=True)

# Explorer
st.subheader("Archetype Leaderboard")
if "archetype" in fdf.columns:
    sel = st.selectbox("Select Archetype", sorted(fdf["archetype"].unique()))
    adf = fdf[fdf["archetype"] == sel]
    scol = "position_score" if "position_score" in adf.columns else "cpa_xGI_p90"
    show = ["player","team","league","position_group","age_bracket","reliability_tier",
            "position_score","position_pctile","cpa_xGI_p90","overall_rating","value_eur"]
    show = [c for c in show if c in adf.columns]
    st.dataframe(adf.nlargest(30, scol)[show].reset_index(drop=True), use_container_width=True)
