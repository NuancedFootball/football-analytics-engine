#!/usr/bin/env python3
"""
Streamlit Dashboard — Nuanced Football PLAYER <> LEAGUE <> TEAM Engine
Entrypoint file. Run with: streamlit run dashboard.py
"""
import streamlit as st

st.set_page_config(
    page_title="Football Analytics Engine",
    page_icon="\u26bd",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Pages ────────────────────────────────────────────────────────────
overview    = st.Page("pages/pg_overview.py",       title="Overview",              icon="\U0001f3e0")
gk_page     = st.Page("pages/pg_gk_profiles.py",    title="GK Profiles",           icon="\U0001f9e4")
team_page   = st.Page("pages/pg_team_ecosystem.py",  title="Team Ecosystems",       icon="\U0001f3df\ufe0f")
xpos_page   = st.Page("pages/pg_cross_positional.py",title="Cross-Positional",      icon="\U0001f504")
compare_page= st.Page("pages/pg_compare.py",         title="Player Compare",        icon="\u2696\ufe0f")

pg = st.navigation({
    "Dashboard":  [overview],
    "Analysis":   [gk_page, team_page, xpos_page],
    "Tools":      [compare_page],
})

# ── Sidebar branding ────────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.caption("Football Analytics Engine v1.0")
st.sidebar.caption("Data: Understat 2024/25 | Big 5 Leagues")

pg.run()
