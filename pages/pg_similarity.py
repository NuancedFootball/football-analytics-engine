import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import pathlib
from glossary import show_glossary, player_card

st.title("Player Similarity Finder")
st.caption("Weighted cosine similarity | SoFIFA player cards")
show_glossary()

SD = pathlib.Path("scraped_data")

@st.cache_data
def load():
    sp = SD / "engine_similarity.csv"
    cp = SD / "engine_cpa_profiles.csv"
    return (pd.read_csv(sp) if sp.exists() else None,
            pd.read_csv(cp) if cp.exists() else None)

sim_df, cpa_df = load()
if sim_df is None:
    st.error("Similarity data not found.")
    st.stop()

players = sorted(sim_df["player"].unique().tolist()) if "player" in sim_df.columns else []
sel = st.selectbox("Select Player", players, key="sim_p")

if sel and len(sim_df[sim_df["player"]==sel]) > 0:
    row = sim_df[sim_df["player"]==sel].iloc[0]

    if cpa_df is not None:
        src = cpa_df[cpa_df["player"]==sel]
        if len(src) > 0:
            player_card(src.iloc[0])

    sim_names = [c for c in sim_df.columns if c.startswith("sim_") and c.endswith("_name")]
    results = []
    for nc in sim_names:
        sc = nc.replace("_name","_score")
        if sc in row.index and pd.notna(row[nc]):
            results.append({"Player": row[nc], "Similarity": round(float(row[sc]),4)})

    if results:
        st.subheader("Top " + str(len(results)) + " Similar Players")
        st.dataframe(pd.DataFrame(results), use_container_width=True, height=500)

        if cpa_df is not None and len(results) > 0:
            top_name = results[0]["Player"]
            comp = cpa_df[cpa_df["player"]==top_name]
            src2 = cpa_df[cpa_df["player"]==sel]
            if len(comp) > 0 and len(src2) > 0:
                rcols = ["cpa_xG_p90","cpa_xA_p90","cpa_xGChain_p90","cpa_xGBuildup_p90",
                         "role_burden","shots_p90","key_passes_p90"]
                rcols = [c for c in rcols if c in cpa_df.columns]
                if rcols:
                    labels = [c.replace("cpa_","").replace("_p90","").replace("_"," ").title() for c in rcols]
                    v1 = [(cpa_df[c] <= src2.iloc[0][c]).mean()*100 for c in rcols]
                    v2 = [(cpa_df[c] <= comp.iloc[0][c]).mean()*100 for c in rcols]
                    fig = go.Figure()
                    fig.add_trace(go.Scatterpolar(r=v1+[v1[0]], theta=labels+[labels[0]],
                                                   fill="toself", name=sel, line_color="#FF6B35"))
                    fig.add_trace(go.Scatterpolar(r=v2+[v2[0]], theta=labels+[labels[0]],
                                                   fill="toself", name=top_name, line_color="#4ECDC4"))
                    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0,100])),
                                      title="Radar: " + sel + " vs " + top_name, height=500)
                    st.plotly_chart(fig, use_container_width=True)
