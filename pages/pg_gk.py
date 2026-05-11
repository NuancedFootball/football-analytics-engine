import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import pathlib
from glossary import show_glossary

st.title("Goalkeeper Profiles")
st.caption("Dedicated GK track | SoFIFA GK attributes")
show_glossary()

SD = pathlib.Path("scraped_data")

@st.cache_data
def load():
    gp = SD / "engine_gk_profiles.csv"
    gs = SD / "engine_gk_similarity.csv"
    return (pd.read_csv(gp) if gp.exists() else None,
            pd.read_csv(gs) if gs.exists() else None)

gk, gk_sim = load()
if gk is None:
    st.warning("GK profiles not found.")
    st.stop()

hide = ["player_id","understat_id"]
show = [c for c in gk.columns if c not in hide]
st.dataframe(gk[show].reset_index(drop=True), use_container_width=True, height=500)

if gk_sim is not None and "player" in gk_sim.columns:
    st.divider()
    st.subheader("GK Similarity")
    sel = st.selectbox("Find similar to", sorted(gk_sim["player"].unique().tolist()), key="gk_s")
    gr = gk_sim[gk_sim["player"]==sel]
    if len(gr) > 0:
        sim_names = [c for c in gk_sim.columns if c.startswith("sim_") and c.endswith("_name")]
        results = []
        for nc in sim_names:
            sc = nc.replace("_name","_score")
            if sc in gr.columns and pd.notna(gr.iloc[0][nc]):
                results.append({"Goalkeeper": gr.iloc[0][nc], "Similarity": round(float(gr.iloc[0][sc]),4)})
        if results:
            st.dataframe(pd.DataFrame(results), use_container_width=True)
