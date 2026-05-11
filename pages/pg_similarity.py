import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import pathlib

st.title("Player Similarity Finder")
st.caption("Weighted cosine similarity across CPA-adjusted features")

SD = pathlib.Path("scraped_data")

@st.cache_data
def load():
    sp = SD / "engine_similarity.csv"
    cp = SD / "engine_cpa_profiles.csv"
    sim = pd.read_csv(sp) if sp.exists() else None
    cpa = pd.read_csv(cp) if cp.exists() else None
    return sim, cpa

sim_df, cpa_df = load()
if sim_df is None:
    st.error("Similarity data not found.")
    st.stop()

players = sorted(sim_df["player"].unique().tolist()) if "player" in sim_df.columns else []
sel = st.selectbox("Select Player", players, key="sim_p")

if sel and len(sim_df[sim_df["player"] == sel]) > 0:
    row = sim_df[sim_df["player"] == sel].iloc[0]

    sim_name_cols = [c for c in sim_df.columns if c.startswith("sim_") and c.endswith("_name")]
    results = []
    for nc in sim_name_cols:
        sc = nc.replace("_name", "_score")
        if sc in row.index and pd.notna(row[nc]):
            results.append({"Player": row[nc], "Similarity": round(float(row[sc]), 4)})

    if results:
        st.subheader("Top " + str(len(results)) + " Similar Players to " + sel)

        if cpa_df is not None:
            src = cpa_df[cpa_df["player"] == sel]
            if len(src) > 0:
                s = src.iloc[0]
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Team", str(s.get("team", "?")))
                c2.metric("Archetype", str(s.get("archetype", "?")))
                c3.metric("CPA xGI/90", round(s.get("cpa_xGI_p90", 0), 3))
                c4.metric("League", str(s.get("league", "?")))

        st.dataframe(pd.DataFrame(results), use_container_width=True, height=500)

        # Overlay radar for top match
        if cpa_df is not None and len(results) > 0:
            top_name = results[0]["Player"]
            comp = cpa_df[cpa_df["player"] == top_name]
            src2 = cpa_df[cpa_df["player"] == sel]
            if len(comp) > 0 and len(src2) > 0:
                rcols = ["cpa_xG_p90","cpa_xA_p90","cpa_xGChain_p90",
                         "cpa_xGBuildup_p90","role_burden","shots_p90",
                         "key_passes_p90"]
                rcols = [c for c in rcols if c in cpa_df.columns]
                if rcols:
                    labels = [c.replace("cpa_","").replace("_p90","")
                              .replace("_"," ").title() for c in rcols]
                    v1 = [(cpa_df[c] <= src2.iloc[0][c]).mean() * 100 for c in rcols]
                    v2 = [(cpa_df[c] <= comp.iloc[0][c]).mean() * 100 for c in rcols]

                    fig = go.Figure()
                    fig.add_trace(go.Scatterpolar(
                        r=v1+[v1[0]], theta=labels+[labels[0]],
                        fill="toself", name=sel, line_color="#FF6B35"))
                    fig.add_trace(go.Scatterpolar(
                        r=v2+[v2[0]], theta=labels+[labels[0]],
                        fill="toself", name=top_name, line_color="#4ECDC4"))
                    fig.update_layout(
                        polar=dict(radialaxis=dict(visible=True, range=[0,100])),
                        title="Radar: " + sel + " vs " + top_name, height=500)
                    st.plotly_chart(fig, use_container_width=True)
