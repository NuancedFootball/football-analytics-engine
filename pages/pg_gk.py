import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import pathlib

st.title("Goalkeeper Profiles")
st.caption("Dedicated GK analytics separated from outfield pipeline")

SD = pathlib.Path("scraped_data")

@st.cache_data
def load():
    gp = SD / "engine_gk_profiles.csv"
    gs = SD / "engine_gk_similarity.csv"
    gk = pd.read_csv(gp) if gp.exists() else None
    gk_sim = pd.read_csv(gs) if gs.exists() else None
    return gk, gk_sim

gk, gk_sim = load()

if gk is None:
    st.warning("GK profiles not found. Requires the GK scraping pipeline.")
    st.stop()

st.subheader("Goalkeeper Database (" + str(len(gk)) + " keepers)")
hide = ["player_id","understat_id"]
show = [c for c in gk.columns if c not in hide]
st.dataframe(gk[show].reset_index(drop=True), use_container_width=True, height=500)

st.divider()
st.subheader("GK Radar")
if "player" in gk.columns:
    gk_list = sorted(gk["player"].unique().tolist())
    sel = st.selectbox("Select Goalkeeper", gk_list, key="gk_s")

    gk_row = gk[gk["player"] == sel]
    if len(gk_row) > 0:
        gk_row = gk_row.iloc[0]
        radar_keys = ["save","xg","psxg","clean","concede","shot"]
        rcols = [c for c in gk.columns
                 if any(k in c.lower() for k in radar_keys)][:8]
        if rcols:
            vals = [(gk[c].dropna() <= gk_row[c]).mean() * 100 for c in rcols]
            labels = [c.replace("_"," ").title() for c in rcols]
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(
                r=vals+[vals[0]], theta=labels+[labels[0]],
                fill="toself", name=sel, line_color="#FF6B35"))
            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0,100])),
                title=sel + " - GK Percentile Radar", height=500)
            st.plotly_chart(fig, use_container_width=True)

if gk_sim is not None:
    st.divider()
    st.subheader("GK Similarity")
    if "player" in gk_sim.columns:
        sel2 = st.selectbox("Find similar to",
                            sorted(gk_sim["player"].unique().tolist()), key="gk_sim_s")
        gr = gk_sim[gk_sim["player"] == sel2]
        if len(gr) > 0:
            sim_names = [c for c in gk_sim.columns
                         if c.startswith("sim_") and c.endswith("_name")]
            results = []
            for nc in sim_names:
                sc = nc.replace("_name","_score")
                if sc in gr.columns and pd.notna(gr.iloc[0][nc]):
                    results.append({"Goalkeeper": gr.iloc[0][nc],
                                    "Similarity": round(float(gr.iloc[0][sc]),4)})
            if results:
                st.dataframe(pd.DataFrame(results), use_container_width=True)
