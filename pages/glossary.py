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
