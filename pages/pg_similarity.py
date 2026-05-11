import streamlit as st
import pandas as pd

st.title("Player Similarity Engine")
D = "scraped_data"

@st.cache_data
def load_sim():
    return pd.read_csv("{}/engine_similarity.csv".format(D))

sim = load_sim()
sel = st.selectbox("Select Player", sorted(sim["player"].unique()))
if sel:
    row = sim[sim["player"]==sel].iloc[0]
    st.markdown("{} ({}, {}) -- Archetype: {}".format(sel, row.get("team",""), row.get("league",""), row.get("archetype","")))
    sim_rows = []
    for k in range(1, 21):
        nm = row.get("sim_{}_name".format(k), "")
        if not nm or pd.isna(nm):
            break
        sim_rows.append({
            "Rank": k,
            "Player": nm,
            "Team": row.get("sim_{}_team".format(k), ""),
            "League": row.get("sim_{}_league".format(k), ""),
            "Archetype": row.get("sim_{}_archetype".format(k), ""),
            "Similarity": row.get("sim_{}_score".format(k), 0),
        })
    sdf = pd.DataFrame(sim_rows)
    st.dataframe(sdf, use_container_width=True, hide_index=True)

    st.subheader("Filter by Target League")
    tgt_lg = st.selectbox("Target League", ["All"] + sorted(sdf["League"].unique().tolist()))
    if tgt_lg != "All":
        st.dataframe(sdf[sdf["League"]==tgt_lg], use_container_width=True, hide_index=True)
