import streamlit as st
import pandas as pd
import plotly.express as px
import pathlib

st.title("Player Archetype Classification")
st.caption("PCA + K-Means clustering on CPA-adjusted feature vectors")

SD = pathlib.Path("scraped_data")

@st.cache_data
def load():
    cp = SD / "engine_cpa_profiles.csv"
    ce = SD / "engine_archetype_centroids.csv"
    cpa = pd.read_csv(cp) if cp.exists() else None
    cent = pd.read_csv(ce) if ce.exists() else None
    return cpa, cent

cpa, centroids = load()
if cpa is None:
    st.error("CPA profiles not found.")
    st.stop()
if "archetype" not in cpa.columns:
    st.warning("No archetype column. Run engine Phase 3.")
    st.stop()

# Filter out GKs from outfield archetypes
if "position" in cpa.columns:
    outfield = cpa[~cpa["position"].str.contains("GK", case=False, na=False)].copy()
else:
    outfield = cpa.copy()

st.subheader("Archetype Distribution (Outfield)")
dist = outfield["archetype"].value_counts().reset_index()
dist.columns = ["archetype", "count"]
fig_d = px.bar(dist, x="archetype", y="count", color="archetype",
               title="Players per Archetype")
fig_d.update_layout(showlegend=False, height=400)
st.plotly_chart(fig_d, use_container_width=True)

pca_cols = [c for c in outfield.columns if c.startswith("pca_")]
if len(pca_cols) >= 2:
    st.subheader("PCA Projection")
    fig_p = px.scatter(outfield, x=pca_cols[0], y=pca_cols[1],
                       color="archetype", hover_name="player",
                       opacity=0.6, title="Archetype Clusters in PCA Space")
    fig_p.update_layout(height=600)
    st.plotly_chart(fig_p, use_container_width=True)

st.subheader("Archetype Explorer")
sel = st.selectbox("Select Archetype", sorted(outfield["archetype"].unique()))
adf = outfield[outfield["archetype"] == sel]
scol = "cpa_xGI_p90" if "cpa_xGI_p90" in adf.columns else adf.columns[0]
show = ["player","team","league","cpa_xGI_p90","cpa_xG_p90","cpa_xA_p90",
        "role_burden","minutes"]
show = [c for c in show if c in adf.columns]
st.dataframe(adf.nlargest(30, scol)[show].reset_index(drop=True),
             use_container_width=True)

if centroids is not None:
    st.subheader("Archetype Centroids")
    st.dataframe(centroids, use_container_width=True)
