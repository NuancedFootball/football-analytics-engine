import streamlit as st
import pandas as pd
import plotly.express as px

st.title("Player Archetype Classification")
D = "scraped_data"

@st.cache_data
def load():
    return pd.read_csv("{}/engine_cpa_profiles.csv".format(D))

df = load()
if "archetype" not in df.columns:
    st.warning("Run build_engine_core.py first to generate archetypes.")
    st.stop()

st.subheader("Archetype Distribution")
dist = df["archetype"].value_counts().reset_index()
dist.columns = ["Archetype", "Count"]
fig = px.bar(dist, x="Archetype", y="Count", color="Archetype")
fig.update_layout(height=400)
st.plotly_chart(fig, use_container_width=True)

if "pca_1" in df.columns and "pca_2" in df.columns:
    st.subheader("Archetype Landscape (PCA)")
    fig2 = px.scatter(df, x="pca_1", y="pca_2", color="archetype", hover_name="player",
                      hover_data=["team","league","cpa_xGI_p90"], opacity=0.7)
    fig2.update_layout(height=600)
    st.plotly_chart(fig2, use_container_width=True)

st.subheader("Explore Archetype")
sel_arch = st.selectbox("Select Archetype", sorted(df["archetype"].unique()))
adf = df[df["archetype"]==sel_arch].sort_values("cpa_xGI_p90", ascending=False)
st.write("{} players in this archetype".format(len(adf)))
show_cols = ["player","team","league","matches","cpa_xG_p90","cpa_xA_p90","cpa_xGI_p90","role_burden"]
avail = [c for c in show_cols if c in adf.columns]
st.dataframe(adf[avail].head(30), use_container_width=True, hide_index=True)

st.subheader("Archetype by League")
cross = pd.crosstab(df["archetype"], df["league"])
st.dataframe(cross, use_container_width=True)
