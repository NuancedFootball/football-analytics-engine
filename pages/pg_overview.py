import streamlit as st
import pandas as pd
import pathlib
from glossary import show_glossary, show_methodology

st.title("Nuanced Football Engine v3.0")
st.caption("Big 5 Leagues | 2025-26 | Understat + SoFIFA + FotMob | 136-column player profiles")

SD = pathlib.Path("scraped_data")
def sl(n):
    p = SD / n
    return pd.read_csv(p) if p.exists() else None

cpa = sl("engine_cpa_profiles.csv")
eco = sl("engine_team_ecosystems_v3.csv")
gk = sl("engine_gk_profiles.csv")

c1,c2,c3,c4,c5 = st.columns(5)
c1.metric("Players", len(cpa) if cpa is not None else "?")
c2.metric("Teams", len(eco) if eco is not None else "?")
c3.metric("GKs", len(gk) if gk is not None else "?")
c4.metric("Leagues", "5")
c5.metric("Columns", len(cpa.columns) if cpa is not None else "?")

show_glossary()
show_methodology()

if cpa is not None:
    st.divider()
    st.subheader("Top 10 by Position Score (per band)")
    for band in ["Attacker","Midfielder","Defender"]:
        sub = cpa[cpa["position_band"]==band].nlargest(5,"position_score") if "position_band" in cpa.columns else pd.DataFrame()
        if len(sub) > 0:
            st.write("**" + band + "s:**")
            cols = ["player","team","position_group","archetype","position_score","position_pctile","age_bracket","reliability_tier"]
            cols = [c for c in cols if c in sub.columns]
            st.dataframe(sub[cols].reset_index(drop=True), use_container_width=True)
