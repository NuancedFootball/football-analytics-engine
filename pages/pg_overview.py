
import streamlit as st
import pandas as pd
import os

st.title("\u26bd Football Analytics Engine")
st.markdown("#### Nuanced PLAYER \u21c4 LEAGUE \u21c4 TEAM Analysis | 2024/25 Big 5 Leagues")
st.markdown("---")

# Load data summaries
data_files = {
    "GK Season Profiles":       "scraped_data/gk_season_profiles.csv",
    "GK Match Logs":            "scraped_data/gk_match_logs.csv",
    "GK Shot Detail":           "scraped_data/gk_shot_facing_detail.csv",
    "GK Engine Profiles":       "scraped_data/engine_gk_profiles.csv",
    "GK Similarity":            "scraped_data/engine_gk_similarity.csv",
    "Team Ecosystems V2":       "scraped_data/engine_team_ecosystems_v2.csv",
    "Cross-Positional":         "scraped_data/engine_cross_positional.csv",
    "Positional Correlations":  "scraped_data/engine_positional_correlations.csv",
    "Team Dependencies":        "scraped_data/engine_team_dependencies.csv",
    "Match Index":              "scraped_data/gk_match_index.csv",
    "Outfield Player Logs":     "scraped_data/understat_player_match_tagged.csv",
    "Outfield Player Profiles": "scraped_data/engine_player_profiles.csv",
}

cols = st.columns(3)
loaded = 0
for i, (name, path) in enumerate(data_files.items()):
    col = cols[i % 3]
    if os.path.exists(path):
        df = pd.read_csv(path, nrows=1)
        rows = sum(1 for _ in open(path)) - 1
        col.metric(name, f"{rows:,} rows", f"{len(df.columns)} cols")
        loaded += 1
    else:
        col.metric(name, "Not found", delta=None)

st.markdown("---")
st.markdown(f"**{loaded}/{len(data_files)}** datasets available.")

st.markdown("""
### Engine Architecture

**Layer 1 — Player Context Profiles**: Per-match and season-aggregated stats for outfield players
and goalkeepers, split by home/away, opponent strength, match state, and zone.

**Layer 2 — Team Ecosystems**: Team-level offensive/defensive identity, including primary GK quality,
xG concentration, buildup ratios, and home/away multipliers.

**Layer 3 — Cross-Positional Dependencies**: How GK shot-stopping correlates with defensive buildup,
midfield creation, and forward output. Reveals which teams are most GK-dependent.

**Layer 4 — Similarity Engine**: Cosine similarity on composite features to find behaviorally
similar players and GKs across leagues.
""")

# Quick stats
if os.path.exists("scraped_data/gk_match_index.csv"):
    idx = pd.read_csv("scraped_data/gk_match_index.csv")
    st.markdown("### Season Coverage")
    league_counts = idx.groupby("league").size().reset_index(name="matches")
    st.dataframe(league_counts, use_container_width=True, hide_index=True)
