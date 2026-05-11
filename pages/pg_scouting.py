import streamlit as st
import pandas as pd

st.title("Scouting Shortlist Builder")
D = "scraped_data"

@st.cache_data
def load_cpa():
    return pd.read_csv(f"{D}/engine_cpa_profiles.csv")

@st.cache_data
def load_sim():
    return pd.read_csv(f"{D}/engine_similarity.csv")

@st.cache_data
def load_ti():
    return pd.read_csv(f"{D}/engine_transfer_intel.csv")

cpa = load_cpa()
sim = load_sim()
ti = load_ti()

st.header("Define Your Search")
c1, c2, c3 = st.columns(3)
with c1:
    target_league = st.multiselect("Target Leagues", sorted(cpa["league"].unique()), default=list(cpa["league"].unique()))
with c2:
    target_archetype = st.multiselect("Archetypes", sorted(cpa["archetype"].dropna().unique()))
with c3:
    target_position = st.multiselect("Positions", sorted(cpa["position"].dropna().unique()))

min_xgi = st.slider("Min CPA xGI/90", 0.0, 1.5, 0.1, 0.05)
min_matches = st.slider("Min Matches", 5, 35, 10)

filtered = cpa.copy()
if target_league:
    filtered = filtered[filtered["league"].isin(target_league)]
if target_archetype:
    filtered = filtered[filtered["archetype"].isin(target_archetype)]
if target_position:
    filtered = filtered[filtered["position"].isin(target_position)]
filtered = filtered[filtered["cpa_xGI_p90"] >= min_xgi]
filtered = filtered[filtered["matches"] >= min_matches]

st.subheader(f"Results: {len(filtered)} players")
display_cols = ["player","team","league","position","archetype","matches","total_minutes",
                "cpa_xGI_p90","cpa_xG_p90","cpa_xA_p90","role_burden",
                "resilience_ratio","big_game_ratio","xG_overperf_p90",
                "pct_6yd","pct_pen","pct_outside"]
available = [c for c in display_cols if c in filtered.columns]
st.dataframe(filtered[available].sort_values("cpa_xGI_p90", ascending=False),
             use_container_width=True, hide_index=True)

st.header("Replacement Finder")
st.markdown("*Select a player to find their closest statistical matches across all leagues.*")
player = st.selectbox("Player to Replace", sim["player"].unique())
pr = sim[sim["player"]==player]
if len(pr) > 0:
    pr = pr.iloc[0]
    st.markdown(f"Finding replacements for **{pr['player']}** ({pr['team']}, {pr.get('archetype','')})")
    rows = []
    for k in range(1, 21):
        n = pr.get(f"sim_{k}_name","")
        if not n: break
        rows.append({
            "Rank": k, "Player": n, "Team": pr.get(f"sim_{k}_team",""),
            "League": pr.get(f"sim_{k}_league",""),
            "Archetype": pr.get(f"sim_{k}_archetype",""),
            "Similarity": pr.get(f"sim_{k}_score",0),
        })
    rdf = pd.DataFrame(rows)
    # Merge transfer score
    rdf = rdf.merge(ti[["player","transfer_score","cpa_xGI_p90"]].rename(columns={"player":"Player"}),
                     on="Player", how="left")
    st.dataframe(rdf, use_container_width=True, hide_index=True)
