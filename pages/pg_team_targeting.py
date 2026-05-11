import streamlit as st
import pandas as pd
import plotly.express as px
import pathlib
from glossary import show_glossary, show_methodology, fmt_value, player_card

st.title("Team Targeting Engine")
st.caption("Gap analysis | Financial feasibility | Position-specific recommendations")
show_glossary()
show_methodology()

SD = pathlib.Path("scraped_data")

@st.cache_data
def load_all():
    cpa = pd.read_csv(SD / "engine_cpa_profiles.csv") if (SD / "engine_cpa_profiles.csv").exists() else None
    eco = pd.read_csv(SD / "engine_team_ecosystems_v3.csv") if (SD / "engine_team_ecosystems_v3.csv").exists() else None
    return cpa, eco

cpa, eco = load_all()
if cpa is None or eco is None:
    st.error("Required data not found.")
    st.stop()

teams = sorted(eco["team"].unique().tolist())
sel_team = st.selectbox("Select Team", teams, key="tt_team")

team_eco = eco[eco["team"]==sel_team]
team_players = cpa[cpa["team"]==sel_team]
team_outfield = team_players[team_players["position_band"] != "Goalkeeper"] if "position_band" in team_players.columns else team_players

if len(team_eco) == 0:
    st.warning("No ecosystem data for this team.")
    st.stop()

te = team_eco.iloc[0]

# ── Team Overview ──
st.subheader("Team Profile: " + sel_team)
c1,c2,c3,c4,c5 = st.columns(5)
c1.metric("xGD", round(te.get("xGD",0),1))
c2.metric("PPG", round(te.get("ppg",0),2))
c3.metric("Squad Value", fmt_value(te.get("squad_value")))
c4.metric("Avg Player Val", fmt_value(te.get("avg_player_value")))
c5.metric("Squad Size", int(te.get("players",0)))

# ── Squad Composition ──
st.subheader("Squad Composition")
if "position_group" in team_outfield.columns:
    pg_dist = team_outfield["position_group"].value_counts().reset_index()
    pg_dist.columns = ["Position","Count"]
    fig_pg = px.bar(pg_dist, x="Position", y="Count", title="Position Group Distribution")
    fig_pg.update_layout(height=300, showlegend=False)
    st.plotly_chart(fig_pg, use_container_width=True)

show = ["player","position_group","archetype","age_bracket","reliability_tier",
        "position_score","position_pctile","cpa_xGI_p90","overall_rating","value_eur"]
show = [c for c in show if c in team_outfield.columns]
st.dataframe(team_outfield[show].sort_values("position_score", ascending=False).reset_index(drop=True),
             use_container_width=True)

# ── Gap Analysis ──
st.divider()
st.subheader("Gap Analysis")

# Position needs
if "position_band" in team_outfield.columns:
    band_counts = team_outfield["position_band"].value_counts().to_dict()
    ideal = {"Attacker": 5, "Midfielder": 5, "Defender": 5}
    gaps = []
    for band, target in ideal.items():
        actual = band_counts.get(band, 0)
        if actual < target:
            gaps.append(band + " (have " + str(actual) + ", need " + str(target) + ")")
    if gaps:
        st.write("Position band gaps: " + ", ".join(gaps))
    else:
        st.write("No critical position band gaps detected.")

# Archetype gaps
if "archetype" in team_outfield.columns:
    team_archs = set(team_outfield["archetype"].unique())
    all_archs = set(cpa[cpa["position_band"] != "Goalkeeper"]["archetype"].dropna().unique())
    missing = all_archs - team_archs
    if missing:
        st.write("Missing archetypes: " + ", ".join(sorted(missing)))

# ── Recommendations ──
st.divider()
st.subheader("Transfer Recommendations")

with st.sidebar:
    st.subheader("Targeting Filters")
    target_band = st.selectbox("Target Position Band", ["All","Attacker","Midfielder","Defender"], key="tt_band")
    target_age = st.selectbox("Target Age Bracket", ["All","Prospect (U21)","Emerging (21-23)","Prime (24-27)","Peak (28-31)","Veteran (32+)"], key="tt_age")
    max_budget = st.slider("Max Budget (EUR M)", 0, 200, 100, step=5, key="tt_budget")
    min_reliability = st.selectbox("Min Reliability", ["All","Elite Sample","Strong Sample","Moderate Sample"], key="tt_rel")

# Build candidate pool
pool = cpa[(cpa["team"] != sel_team) & (cpa["position_band"] != "Goalkeeper")].copy()

if target_band != "All":
    pool = pool[pool["position_band"] == target_band]
if target_age != "All" and "age_bracket" in pool.columns:
    pool = pool[pool["age_bracket"] == target_age]
if max_budget < 200 and "value_eur" in pool.columns:
    pool = pool[(pool["value_eur"].fillna(0) <= max_budget * 1e6) | pool["value_eur"].isna()]
if min_reliability != "All" and "reliability_tier" in pool.columns:
    tier_order = {"Elite Sample":5,"Strong Sample":4,"Moderate Sample":3,"Limited Sample":2,"Small Sample":1}
    min_val = tier_order.get(min_reliability, 0)
    pool["_tn"] = pool["reliability_tier"].map(tier_order).fillna(0)
    pool = pool[pool["_tn"] >= min_val].drop(columns=["_tn"])

# Score candidates with financial feasibility
squad_val = te.get("squad_value", 500e6)
avg_val = te.get("avg_player_value", 30e6)

if "value_eur" in pool.columns and "position_score" in pool.columns:
    pool["affordability"] = pool["value_eur"].apply(
        lambda v: round(1.0 - min(float(v or 0) / max(avg_val * 2, 1), 1.0), 3)
    )
    pool["fit_score"] = (
        pool["position_pctile"].fillna(50) / 100 * 0.40 +
        pool["affordability"] * 0.25 +
        pool["resilience_ratio"].fillna(0) * 0.15 +
        pool["big_game_ratio"].fillna(0) * 0.10 +
        pool.get("discount_score", pd.Series(0, index=pool.index)).fillna(0).clip(upper=5) / 5 * 0.10
    ).round(4)
else:
    pool["fit_score"] = pool.get("position_pctile", pd.Series(50, index=pool.index)).fillna(50) / 100

rec = pool.nlargest(20, "fit_score")

rec_show = ["player","team","league","position_group","archetype","age_bracket",
            "reliability_tier","position_pctile","fit_score","overall_rating",
            "value_eur","discount_score","cpa_xGI_p90"]
rec_show = [c for c in rec_show if c in rec.columns]

st.write("Top " + str(len(rec)) + " candidates from " + str(len(pool)) + " in pool:")
display = rec[rec_show].reset_index(drop=True)
display.index = display.index + 1
st.dataframe(display, use_container_width=True, height=500)

# ── Detailed recommendation card ──
if len(rec) > 0:
    st.divider()
    st.subheader("Recommendation Deep Dive")
    sel_rec = st.selectbox("Select Recommendation", rec["player"].tolist(), key="tt_rec")
    rec_row = rec[rec["player"]==sel_rec].iloc[0]
    player_card(rec_row)

    st.write("**Why this player fits " + sel_team + ":**")
    reasons = []
    if rec_row.get("position_pctile", 0) >= 75:
        reasons.append("Top quartile in position group (" + str(rec_row.get("position_group","")) + " at " + str(round(rec_row.get("position_pctile",0),1)) + "th percentile)")
    val = rec_row.get("value_eur", 0)
    if pd.notna(val) and val > 0 and val <= avg_val:
        reasons.append("Below team average player value (" + fmt_value(val) + " vs " + fmt_value(avg_val) + " avg)")
    elif pd.notna(val) and val > 0:
        pct = round(val / avg_val * 100)
        reasons.append("Costs " + str(pct) + "% of team avg player value (" + fmt_value(val) + ")")
    if rec_row.get("resilience_ratio", 0) > team_outfield["resilience_ratio"].mean():
        reasons.append("Higher resilience than squad average")
    if rec_row.get("big_game_ratio", 0) > team_outfield["big_game_ratio"].mean():
        reasons.append("Stronger big-game performance than squad average")
    ds = rec_row.get("discount_score", 0)
    if pd.notna(ds) and ds > 2:
        reasons.append("High discount score (" + str(round(ds,1)) + ") = strong performance relative to cost")
    if rec_row.get("age_bracket","") in ["Prospect (U21)","Emerging (21-23)"]:
        reasons.append("Young profile with long-term value and development upside")
    if rec_row.get("reliability_tier","") in ["Elite Sample","Strong Sample"]:
        reasons.append("High reliability tier = proven over substantial minutes")
    if not reasons:
        reasons.append("Balanced profile that complements the existing squad")
    for r in reasons:
        st.write("- " + r)

    st.divider()
    csv = display.to_csv(index=False)
    fname = sel_team.lower().replace(" ","_") + "_recommendations.csv"
    st.download_button("Download Recommendations CSV", csv, fname, "text/csv")
