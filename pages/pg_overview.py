import streamlit as st
import pandas as pd
import os

st.title("Nuanced PLAYER - LEAGUE - TEAM Analytics Engine v2.0")
st.markdown("Big 5 Leagues | 2025/26 Season | Data-Led Professional Scouting")

D = "scraped_data"
inventory = []
for f in sorted(os.listdir(D)):
    if f.endswith(".csv"):
        fp = os.path.join(D, f)
        try:
            df = pd.read_csv(fp, nrows=2)
            rows = sum(1 for _ in open(fp)) - 1
            inventory.append({"File": f, "Rows": "{:,}".format(rows), "Columns": len(df.columns)})
        except Exception:
            inventory.append({"File": f, "Rows": "?", "Columns": "?"})

st.subheader("Data Inventory")
st.dataframe(pd.DataFrame(inventory), use_container_width=True, hide_index=True)

st.subheader("Engine Architecture")
st.markdown(
    "The engine operates across 7 analytical phases, each building on the last:\n\n"
    "Phase 1 - Expected Threat (xT): A value surface over the pitch, computed iteratively from 40K+ shots. "
    "Every zone gets a threat score representing the probability of scoring within the next N actions. "
    "Surfaces are built globally, per-league, and per-team to create threat fingerprints.\n\n"
    "Phase 2 - Contextual Performance Adjustment (CPA): Raw per-90 stats are adjusted by three factors: "
    "League Difficulty Index (scoring environment), Opponent Quality Adjustment (defensive strength of opponents faced), "
    "and Role Burden Index (player share of team output).\n\n"
    "Phase 3 - Archetype Classification: PCA followed by K-means clustering produces functional archetypes "
    "(Clinical Finisher, Creative Conductor, Deep Playmaker, Engine Room, etc.)\n\n"
    "Phase 4 - Similarity Engine: Weighted cosine similarity across CPA-adjusted features finds "
    "the 20 most statistically similar players for every player in the database.\n\n"
    "Phase 5 - Team Ecosystems: Herfindahl concentration indices for creativity, goal threat, "
    "and buildup distribution, plus xT threat corridors and archetype diversity scores.\n\n"
    "Phase 6 - Adversity Profiles: Resilience ratio (output when trailing), big-game ratio "
    "(output vs top defenses), and home/away delta quantify robustness.\n\n"
    "Phase 7 - Transfer Intelligence: Composite scoring combining CPA output, efficiency, "
    "growth signals, and adversity metrics to rank transfer targets."
)
