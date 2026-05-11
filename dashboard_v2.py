import streamlit as st

st.set_page_config(
    page_title="Nuanced Football Engine v2.0",
    page_icon=":material/sports_soccer:",
    layout="wide",
    initial_sidebar_state="expanded",
)

overview    = st.Page("pages/pg_overview.py",          title="Overview",              icon=":material/dashboard:")
xt_surface  = st.Page("pages/pg_xt_surface.py",        title="xT Surfaces",           icon=":material/grid_on:")
cpa_player  = st.Page("pages/pg_player_profiles.py",   title="Player Profiles (CPA)", icon=":material/person_search:")
archetypes  = st.Page("pages/pg_archetypes.py",        title="Archetypes",            icon=":material/category:")
similarity  = st.Page("pages/pg_similarity.py",        title="Similarity Finder",     icon=":material/hub:")
ecosystems  = st.Page("pages/pg_ecosystems.py",        title="Team Ecosystems",       icon=":material/workspaces:")
targeting   = st.Page("pages/pg_team_targeting.py",     title="Team Targeting",        icon=":material/target:")
adversity   = st.Page("pages/pg_adversity.py",         title="Adversity & Resilience",icon=":material/psychology:")
transfer    = st.Page("pages/pg_transfer.py",          title="Transfer Intelligence", icon=":material/trending_up:")
gk_profiles = st.Page("pages/pg_gk.py",               title="GK Profiles",           icon=":material/sports:")
compare     = st.Page("pages/pg_compare.py",           title="Head-to-Head Compare",  icon=":material/compare_arrows:")
shortlist   = st.Page("pages/pg_shortlist.py",         title="Scouting Shortlist",    icon=":material/checklist:")

pg = st.navigation({
    "Overview":    [overview],
    "Threat Model":[xt_surface],
    "Players":     [cpa_player, archetypes, similarity, compare],
    "Teams":       [ecosystems, targeting],
    "Scouting":    [adversity, transfer, gk_profiles, shortlist],
})
pg.run()
