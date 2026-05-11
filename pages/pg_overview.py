import streamlit as st
import pandas as pd
import pathlib

st.title("Nuanced Player - League - Team Engine v2.0")
st.caption("Big 5 Leagues | 2025-26 Season | Understat + SoFIFA + FotMob")

SD = pathlib.Path("scraped_data")

def safe_load(name):
    p = SD / name
    if p.exists():
        return pd.read_csv(p)
    return None

cpa = safe_load("engine_cpa_profiles.csv")
eco = safe_load("engine_team_ecosystems_v3.csv")
gk  = safe_load("engine_gk_profiles.csv")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Outfield Players", len(cpa) if cpa is not None else "N/A")
col2.metric("Teams Profiled", len(eco) if eco is not None else "N/A")
col3.metric("GK Profiles", len(gk) if gk is not None else "N/A")
col4.metric("Leagues", "5")

st.divider()
st.subheader("How It Works")

desc = (
    "The engine processes shot-level data, player match logs, and team "
    "statistics through seven analytical phases. Phase 1 builds Expected "
    "Threat (xT) value surfaces on a pitch grid computed iteratively from "
    "shot data. Phase 2 constructs Contextual Performance Adjustment (CPA) "
    "profiles that normalize output using League Difficulty Index, Opponent "
    "Quality Adjustment, and Role Burden Index. Phase 3 classifies players "
    "into behavioral archetypes via PCA and K-Means. Phase 4 computes "
    "weighted cosine similarity. Phase 5 profiles team ecosystems. Phase 6 "
    "measures adversity and resilience. Phase 7 synthesizes everything into "
    "Transfer Intelligence scores."
)
st.write(desc)

if cpa is not None:
    st.divider()
    st.subheader("Top 15 CPA-Adjusted Players (xGI per 90)")
    cols = ["player","team","league","cpa_xGI_p90","archetype","matches","minutes"]
    cols = [c for c in cols if c in cpa.columns]
    top = cpa.nlargest(15, "cpa_xGI_p90")[cols].reset_index(drop=True)
    top.index = top.index + 1
    st.dataframe(top, use_container_width=True)

if eco is not None:
    st.divider()
    st.subheader("Top 10 Team Ecosystems (xGD)")
    xgd_col = "xGD" if "xGD" in eco.columns else "xgd"
    if xgd_col in eco.columns:
        ecols = ["team","league",xgd_col,"ppg"]
        ecols = [c for c in ecols if c in eco.columns]
        top_eco = eco.nlargest(10, xgd_col)[ecols].reset_index(drop=True)
        top_eco.index = top_eco.index + 1
        st.dataframe(top_eco, use_container_width=True)
