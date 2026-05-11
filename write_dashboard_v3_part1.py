#!/usr/bin/env python3
"""Dashboard v3 Part 1: Glossary module, entry point, overview, player profiles, archetypes, compare"""
import pathlib

count = 0
def write(path, text):
    global count
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    count += 1
    print("  [" + str(count).zfill(2) + "] " + path + " (" + str(len(text)) + " bytes)")

# ============================================================
# Shared glossary module (imported by all pages)
# ============================================================
write("pages/glossary.py", """\
import streamlit as st

def show_glossary():
    with st.expander("Glossary & Abbreviation Key", expanded=False):
        st.markdown('''
**CPA (Contextual Performance Adjustment):** Raw stats adjusted for League Difficulty (LDI),
Opponent Quality (OQA), and Role Burden (RBI) to normalize output across different competitive contexts.

**LDI (League Difficulty Index):** Measures how hard it is to score in a given league. Serie A (1.15) is
the toughest; Bundesliga (0.85) the most open. Computed from average goals per match.

**OQA (Opponent Quality Adjustment):** Per-opponent multiplier based on their defensive xGA.
Playing against Arsenal (low xGA) earns a higher OQA than playing against a relegation side.

**RBI (Role Burden Index):** The proportion of team xG that flows through this player. High RBI
means the team depends heavily on this player for attacking output.

**xGI (Expected Goal Involvement):** xG + xA combined. CPA xGI adjusts this for context.

**Position Score:** A composite metric weighted differently by position band. Attackers are
weighted toward xG/xA, midfielders toward xA/xGChain/xGBuildup, defenders toward
buildup/resilience/big-game ratio. Includes a minutes reliability multiplier (0.6x for small
samples up to 1.0x for elite samples).

**Position Percentile:** Rank within the specific position group (e.g., how a Centre-Back
compares to all other Centre-Backs, not to Strikers).

**Reliability Tier:** Based on total minutes played this season: Elite (2700+), Strong (1800+),
Moderate (1350+), Limited (900+), Small (under 900).

**Discount Score:** Performance-per-value ratio. Higher = better bargain. Computed as
position percentile divided by value percentile. A player in the 90th percentile of performance
who costs in the 30th percentile of value would have a high discount score.

**Archetype Definitions:**
- *Clinical Finisher:* High xG/90, high shot volume, penalty area focus, goal-centric output
- *Creative Conductor:* High xA/90, high key passes, elevated xGChain, creative hub
- *Deep Playmaker:* Moderate xA, high xGBuildup, wide passing range, progressive contribution
- *Pressure Player:* Low offensive output but high defensive resilience and big-game ratios
- *Goalkeeper:* Dedicated GK track, evaluated separately from outfield players

**Age Brackets:**
- Prospect (U21): High development potential, limited sample
- Emerging (21-23): Establishing themselves, strong growth trajectory
- Prime (24-27): Peak physical and tactical development
- Peak (28-31): Maximum output, declining resale value
- Veteran (32+): Experience-driven, limited long-term investment value
''')

def show_methodology():
    with st.expander("Scoring Methodology", expanded=False):
        st.markdown('''
**Position-Weighted Scoring** evaluates players relative to positional expectations rather
than applying a universal metric. The composite score applies different feature weights
depending on the player's position band:

*Attackers* (Strikers, Wingers, Attacking Mids): 35% CPA xG, 20% CPA xA, 15% xGChain,
10% Role Burden, 10% Resilience, 10% Big-Game Ratio.

*Midfielders* (Central, Defensive, Wide Mids): 25% CPA xA, 20% xGChain, 20% xGBuildup,
10% CPA xG, 10% Role Burden, 15% Resilience.

*Defenders* (Centre-Backs, Full-Backs): 30% xGBuildup, 25% Resilience, 20% Big-Game Ratio,
15% xGChain, 10% Role Burden.

All scores are then multiplied by a **Minutes Reliability Factor**: 1.0 for 2700+ minutes,
0.95 for 1800+, 0.85 for 1350+, 0.75 for 900+, 0.60 for under 900. This prevents small-sample
outliers from dominating leaderboards.
''')

def fmt_value(v):
    if v is None or str(v) == "nan":
        return "N/A"
    v = float(v)
    if v >= 1e9:
        return str(round(v / 1e9, 2)) + "B"
    if v >= 1e6:
        return str(round(v / 1e6, 1)) + "M"
    if v >= 1e3:
        return str(round(v / 1e3, 0)) + "K"
    return str(int(v))

def player_card(row):
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Age", int(row["age"]) if "age" in row and str(row.get("age","")) != "nan" else "?")
    c2.metric("OVR / POT",
              str(int(row.get("overall_rating",0))) + " / " + str(int(row.get("potential",0)))
              if "overall_rating" in row and str(row.get("overall_rating","")) != "nan" else "?")
    c3.metric("Value", fmt_value(row.get("value_eur")))
    c4.metric("Height",
              str(int(row.get("height_cm",0))) + "cm"
              if "height_cm" in row and str(row.get("height_cm","")) != "nan" else "?")
    c5.metric("Foot", str(row.get("preferred_foot","?"))
              if str(row.get("preferred_foot","")) != "nan" else "?")

    c6, c7, c8, c9 = st.columns(4)
    c6.metric("Position", str(row.get("position_group","?")))
    c7.metric("Archetype", str(row.get("archetype","?")))
    c8.metric("Age Bracket", str(row.get("age_bracket","?")))
    c9.metric("Reliability", str(row.get("reliability_tier","?")))

def sidebar_filters(df, prefix="pf"):
    with st.sidebar:
        st.subheader("Filters")

        leagues = ["All"] + sorted(df["league"].unique().tolist()) if "league" in df.columns else ["All"]
        sel_league = st.selectbox("League", leagues, key=prefix+"_lg")

        pos_bands = ["All"] + sorted([x for x in df["position_band"].unique().tolist() if x != "Other"]) if "position_band" in df.columns else ["All"]
        sel_band = st.selectbox("Position Band", pos_bands, key=prefix+"_pb")

        pos_groups = ["All"]
        if "position_group" in df.columns:
            if sel_band != "All":
                sub = df[df["position_band"] == sel_band]
                pos_groups += sorted(sub["position_group"].unique().tolist())
            else:
                pos_groups += sorted([x for x in df["position_group"].unique().tolist() if x not in ["Other","Rotation"]])
        sel_group = st.selectbox("Position Group", pos_groups, key=prefix+"_pg")

        archetypes = ["All"] + sorted(df["archetype"].dropna().unique().tolist()) if "archetype" in df.columns else ["All"]
        sel_arch = st.selectbox("Archetype", archetypes, key=prefix+"_ar")

        age_brackets = ["All"] + sorted(df["age_bracket"].dropna().unique().tolist()) if "age_bracket" in df.columns else ["All"]
        sel_age = st.selectbox("Age Bracket", age_brackets, key=prefix+"_ab")

        rel_tiers = ["All"] + ["Elite Sample","Strong Sample","Moderate Sample","Limited Sample","Small Sample"]
        sel_rel = st.selectbox("Min Reliability", rel_tiers, key=prefix+"_rt")

        max_val = st.slider("Max Value (EUR millions)", 0, 200, 200, step=5, key=prefix+"_mv")

    fdf = df.copy()
    if sel_league != "All":
        fdf = fdf[fdf["league"] == sel_league]
    if sel_band != "All" and "position_band" in fdf.columns:
        fdf = fdf[fdf["position_band"] == sel_band]
    if sel_group != "All" and "position_group" in fdf.columns:
        fdf = fdf[fdf["position_group"] == sel_group]
    if sel_arch != "All" and "archetype" in fdf.columns:
        fdf = fdf[fdf["archetype"] == sel_arch]
    if sel_age != "All" and "age_bracket" in fdf.columns:
        fdf = fdf[fdf["age_bracket"] == sel_age]
    if sel_rel != "All" and "reliability_tier" in fdf.columns:
        tier_order = {"Elite Sample":5,"Strong Sample":4,"Moderate Sample":3,"Limited Sample":2,"Small Sample":1}
        min_tier = tier_order.get(sel_rel, 0)
        fdf["_tier_num"] = fdf["reliability_tier"].map(tier_order).fillna(0)
        fdf = fdf[fdf["_tier_num"] >= min_tier].drop(columns=["_tier_num"])
    if max_val < 200 and "value_eur" in fdf.columns:
        fdf = fdf[(fdf["value_eur"].fillna(0) <= max_val * 1e6) | (fdf["value_eur"].isna())]

    return fdf
""")

# ============================================================
# dashboard_v2.py (entry point)
# ============================================================
write("dashboard_v2.py", """\
import streamlit as st

st.set_page_config(
    page_title="Nuanced Football Engine v3.0",
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
targeting   = st.Page("pages/pg_team_targeting.py",    title="Team Targeting",        icon=":material/target:")
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
""")

# ============================================================
# PAGE: Overview
# ============================================================
write("pages/pg_overview.py", """\
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
""")

# ============================================================
# PAGE: Player Profiles (CPA) with SoFIFA cards
# ============================================================
write("pages/pg_player_profiles.py", """\
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import pathlib
from glossary import show_glossary, show_methodology, player_card, sidebar_filters

st.title("Player Profiles (CPA-Adjusted)")
st.caption("Position-weighted scoring | SoFIFA attributes | Contextual normalization")

SD = pathlib.Path("scraped_data")

@st.cache_data
def load():
    return pd.read_csv(SD / "engine_cpa_profiles.csv") if (SD / "engine_cpa_profiles.csv").exists() else None

df = load()
if df is None:
    st.error("CPA profiles not found.")
    st.stop()

show_glossary()
fdf = sidebar_filters(df, prefix="pp")

st.subheader("Leaderboard (" + str(len(fdf)) + " players)")
sort_opts = ["position_score","position_pctile","cpa_xGI_p90","cpa_xG_p90","cpa_xA_p90","discount_score"]
sort_opts = [c for c in sort_opts if c in fdf.columns]
sort_col = st.selectbox("Sort by", sort_opts, key="pp_sort")

display_cols = ["player","team","league","position_group","archetype","age_bracket",
                "reliability_tier","position_score","position_pctile","cpa_xGI_p90",
                "overall_rating","value_eur","discount_score"]
display_cols = [c for c in display_cols if c in fdf.columns]
st.dataframe(fdf.nlargest(50, sort_col)[display_cols].reset_index(drop=True),
             use_container_width=True, height=600)

st.divider()
st.subheader("Player Card & Radar")
player_list = sorted(fdf["player"].unique().tolist())
if player_list:
    sel_p = st.selectbox("Select Player", player_list, key="pp_sel")
    row = fdf[fdf["player"] == sel_p].iloc[0]

    player_card(row)

    st.divider()

    # Position-appropriate radar
    band = row.get("position_band", "Other")
    if band == "Attacker":
        radar_cols = ["cpa_xG_p90","cpa_xA_p90","shots_p90","key_passes_p90","cpa_xGChain_p90","role_burden","resilience_ratio","big_game_ratio"]
    elif band == "Midfielder":
        radar_cols = ["cpa_xA_p90","cpa_xGChain_p90","cpa_xGBuildup_p90","cpa_xG_p90","key_passes_p90","role_burden","resilience_ratio"]
    elif band == "Defender":
        radar_cols = ["cpa_xGBuildup_p90","cpa_xGChain_p90","resilience_ratio","big_game_ratio","role_burden","key_passes_p90"]
    else:
        radar_cols = ["cpa_xGI_p90","resilience_ratio","big_game_ratio","role_burden"]

    radar_cols = [c for c in radar_cols if c in fdf.columns]

    if radar_cols:
        # Compare within position group
        pg = row.get("position_group", "All")
        comp = fdf[fdf["position_group"] == pg] if pg != "All" and "position_group" in fdf.columns else fdf
        vals = []
        for c in radar_cols:
            pctl = (comp[c] <= row[c]).mean()
            vals.append(round(pctl * 100, 1))

        labels = [c.replace("cpa_","").replace("_p90","").replace("_"," ").title() for c in radar_cols]

        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=vals + [vals[0]], theta=labels + [labels[0]],
            fill="toself", name=sel_p, line_color="#FF6B35"
        ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0,100])),
            showlegend=False,
            title=sel_p + " - Percentile Radar vs " + pg + " (" + str(len(comp)) + " players)",
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)

    # SoFIFA technical attributes
    tech_cols = ["finishing","dribbling","short_passing","vision","composure",
                 "sprint_speed","stamina","strength","defensive_awareness","standing_tackle"]
    tech_available = [c for c in tech_cols if c in row.index and str(row.get(c,"")) != "nan"]
    if tech_available:
        st.subheader("SoFIFA Technical Profile")
        tc1, tc2, tc3, tc4, tc5 = st.columns(5)
        for i, c in enumerate(tech_available[:10]):
            col = [tc1,tc2,tc3,tc4,tc5][i % 5]
            col.metric(c.replace("_"," ").title(), int(row[c]))

show_methodology()
""")

# ============================================================
# PAGE: Archetypes with innovative filter panel
# ============================================================
write("pages/pg_archetypes.py", """\
import streamlit as st
import pandas as pd
import plotly.express as px
import pathlib
from glossary import show_glossary, sidebar_filters

st.title("Player Archetype Explorer")
st.caption("PCA + K-Means | Filter by position, age, minutes, league, value")

SD = pathlib.Path("scraped_data")

@st.cache_data
def load():
    cp = SD / "engine_cpa_profiles.csv"
    return pd.read_csv(cp) if cp.exists() else None

cpa = load()
if cpa is None:
    st.error("CPA profiles not found.")
    st.stop()

show_glossary()

# Filter out GKs from display
if "position_band" in cpa.columns:
    outfield = cpa[cpa["position_band"] != "Goalkeeper"].copy()
else:
    outfield = cpa.copy()

fdf = sidebar_filters(outfield, prefix="at")

st.subheader("Archetype Distribution (" + str(len(fdf)) + " players)")
if "archetype" in fdf.columns:
    dist = fdf["archetype"].value_counts().reset_index()
    dist.columns = ["archetype","count"]
    fig_d = px.bar(dist, x="archetype", y="count", color="archetype",
                   title="Filtered Archetype Counts")
    fig_d.update_layout(showlegend=False, height=350)
    st.plotly_chart(fig_d, use_container_width=True)

# Cross-tab: Archetype x Position Band
if "archetype" in fdf.columns and "position_band" in fdf.columns:
    st.subheader("Archetype by Position Band")
    ct = pd.crosstab(fdf["archetype"], fdf["position_band"])
    st.dataframe(ct, use_container_width=True)

# PCA scatter
pca_cols = [c for c in fdf.columns if c.startswith("pca_")]
if len(pca_cols) >= 2 and "archetype" in fdf.columns:
    st.subheader("PCA Projection (colored by archetype)")
    fig_p = px.scatter(fdf, x=pca_cols[0], y=pca_cols[1],
                       color="archetype", hover_name="player",
                       symbol="position_band" if "position_band" in fdf.columns else None,
                       opacity=0.6, title="Clusters in PCA Space")
    fig_p.update_layout(height=600)
    st.plotly_chart(fig_p, use_container_width=True)

# Explorer
st.subheader("Archetype Leaderboard")
if "archetype" in fdf.columns:
    sel = st.selectbox("Select Archetype", sorted(fdf["archetype"].unique()))
    adf = fdf[fdf["archetype"] == sel]
    scol = "position_score" if "position_score" in adf.columns else "cpa_xGI_p90"
    show = ["player","team","league","position_group","age_bracket","reliability_tier",
            "position_score","position_pctile","cpa_xGI_p90","overall_rating","value_eur"]
    show = [c for c in show if c in adf.columns]
    st.dataframe(adf.nlargest(30, scol)[show].reset_index(drop=True), use_container_width=True)
""")

# ============================================================
# PAGE: Compare with SoFIFA cards
# ============================================================
write("pages/pg_compare.py", """\
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import pathlib
from glossary import show_glossary, player_card, fmt_value

st.title("Head-to-Head Player Comparison")
st.caption("Side-by-side CPA profiles with SoFIFA attributes and positional radars")

SD = pathlib.Path("scraped_data")

@st.cache_data
def load():
    return pd.read_csv(SD / "engine_cpa_profiles.csv") if (SD / "engine_cpa_profiles.csv").exists() else None

df = load()
if df is None:
    st.error("CPA profiles not found.")
    st.stop()

show_glossary()

players = sorted(df["player"].unique().tolist())
c1, c2 = st.columns(2)
with c1:
    p1 = st.selectbox("Player A", players, index=0, key="cmp_a")
with c2:
    p2 = st.selectbox("Player B", players, index=min(1,len(players)-1), key="cmp_b")

r1 = df[df["player"]==p1]
r2 = df[df["player"]==p2]
if len(r1)==0 or len(r2)==0:
    st.warning("Select two valid players.")
    st.stop()
r1, r2 = r1.iloc[0], r2.iloc[0]

col1, col2 = st.columns(2)
with col1:
    st.subheader(p1)
    player_card(r1)
with col2:
    st.subheader(p2)
    player_card(r2)

# Radar
radar_cols = ["cpa_xG_p90","cpa_xA_p90","cpa_xGChain_p90","cpa_xGBuildup_p90",
              "role_burden","resilience_ratio","big_game_ratio","shots_p90","key_passes_p90"]
radar_cols = [c for c in radar_cols if c in df.columns]

if radar_cols:
    labels = [c.replace("cpa_","").replace("_p90","").replace("_"," ").title() for c in radar_cols]
    v1 = [(df[c] <= r1[c]).mean()*100 for c in radar_cols]
    v2 = [(df[c] <= r2[c]).mean()*100 for c in radar_cols]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=v1+[v1[0]], theta=labels+[labels[0]],
                                   fill="toself", name=p1, line_color="#FF6B35"))
    fig.add_trace(go.Scatterpolar(r=v2+[v2[0]], theta=labels+[labels[0]],
                                   fill="toself", name=p2, line_color="#4ECDC4"))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0,100])),
                      title="Percentile Radar: " + p1 + " vs " + p2, height=550)
    st.plotly_chart(fig, use_container_width=True)

# Stat comparison table
st.subheader("Full Stat Comparison")
compare_cols = ["cpa_xGI_p90","cpa_xG_p90","cpa_xA_p90","position_score","position_pctile",
                "role_burden","resilience_ratio","big_game_ratio","total_minutes","matches",
                "overall_rating","potential","value_eur","age","height_cm"]
compare_cols = [c for c in compare_cols if c in df.columns]
rows = []
for c in compare_cols:
    label = c.replace("cpa_","").replace("_p90"," /90").replace("_"," ").title()
    v1_val = r1[c]
    v2_val = r2[c]
    if c == "value_eur":
        rows.append({"Metric": label, p1: fmt_value(v1_val), p2: fmt_value(v2_val)})
    else:
        rows.append({"Metric": label,
                      p1: round(v1_val,3) if isinstance(v1_val,float) else v1_val,
                      p2: round(v2_val,3) if isinstance(v2_val,float) else v2_val})
st.dataframe(pd.DataFrame(rows), use_container_width=True)
""")

print()
print("=" * 60)
print("Part 1 complete: " + str(count) + " files written")
print("=" * 60)
print("Run Part 2 next for remaining pages.")
