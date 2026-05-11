#!/usr/bin/env python3
"""Dashboard v3 Part 2: xT, similarity, ecosystems, adversity, transfer, GK, shortlist, team targeting"""
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
# xT Surfaces (keep existing, add glossary)
# ============================================================
write("pages/pg_xt_surface.py", """\
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import pathlib
from glossary import show_glossary

st.title("Expected Threat (xT) Surfaces")
st.caption("Pitch grid | Iterative value computation from shot-level data")
show_glossary()

SD = pathlib.Path("scraped_data")

@st.cache_data
def load_xt():
    lp = SD / "engine_xt_league.csv"
    tp = SD / "engine_xt_team.csv"
    return (pd.read_csv(lp) if lp.exists() else None,
            pd.read_csv(tp) if tp.exists() else None)

league_df, team_df = load_xt()
if league_df is None:
    st.error("xT data not found.")
    st.stop()

def extract_grid(sub):
    val_cols = [c for c in sub.columns if c.startswith("col_")]
    if val_cols:
        return sub[val_cols].values
    numeric = sub.select_dtypes(include=[np.number]).columns.tolist()
    non_meta = [c for c in numeric if c not in ["row","league"]]
    return sub[non_meta].values if non_meta else np.zeros((12,16))

tab1, tab2 = st.tabs(["League xT", "Team xT"])
with tab1:
    opts = sorted(league_df["league"].unique().tolist()) if "league" in league_df.columns else ["GLOBAL"]
    sel = st.selectbox("League", opts, key="xt_l")
    sub = league_df[league_df["league"]==sel] if "league" in league_df.columns else league_df
    grid = extract_grid(sub)
    fig = go.Figure(data=go.Heatmap(z=grid, colorscale="YlOrRd", colorbar=dict(title="xT")))
    fig.update_layout(title="xT: " + sel, xaxis_title="Width", yaxis_title="Length",
                      height=500, yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig, use_container_width=True)
    c1,c2 = st.columns(2)
    c1.metric("Max xT", round(float(grid.max()),4))
    c2.metric("Mean xT", round(float(grid.mean()),6))

with tab2:
    if team_df is not None and len(team_df) > 0:
        tcol = "team" if "team" in team_df.columns else team_df.columns[0]
        sel_t = st.selectbox("Team", sorted(team_df[tcol].unique().tolist()), key="xt_t")
        tsub = team_df[team_df[tcol]==sel_t]
        tgrid = extract_grid(tsub)
        fig2 = go.Figure(data=go.Heatmap(z=tgrid, colorscale="YlOrRd", colorbar=dict(title="xT")))
        fig2.update_layout(title="xT: " + sel_t, height=500, yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig2, use_container_width=True)
""")

# ============================================================
# Similarity
# ============================================================
write("pages/pg_similarity.py", """\
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import pathlib
from glossary import show_glossary, player_card

st.title("Player Similarity Finder")
st.caption("Weighted cosine similarity | SoFIFA player cards")
show_glossary()

SD = pathlib.Path("scraped_data")

@st.cache_data
def load():
    sp = SD / "engine_similarity.csv"
    cp = SD / "engine_cpa_profiles.csv"
    return (pd.read_csv(sp) if sp.exists() else None,
            pd.read_csv(cp) if cp.exists() else None)

sim_df, cpa_df = load()
if sim_df is None:
    st.error("Similarity data not found.")
    st.stop()

players = sorted(sim_df["player"].unique().tolist()) if "player" in sim_df.columns else []
sel = st.selectbox("Select Player", players, key="sim_p")

if sel and len(sim_df[sim_df["player"]==sel]) > 0:
    row = sim_df[sim_df["player"]==sel].iloc[0]

    if cpa_df is not None:
        src = cpa_df[cpa_df["player"]==sel]
        if len(src) > 0:
            player_card(src.iloc[0])

    sim_names = [c for c in sim_df.columns if c.startswith("sim_") and c.endswith("_name")]
    results = []
    for nc in sim_names:
        sc = nc.replace("_name","_score")
        if sc in row.index and pd.notna(row[nc]):
            results.append({"Player": row[nc], "Similarity": round(float(row[sc]),4)})

    if results:
        st.subheader("Top " + str(len(results)) + " Similar Players")
        st.dataframe(pd.DataFrame(results), use_container_width=True, height=500)

        if cpa_df is not None and len(results) > 0:
            top_name = results[0]["Player"]
            comp = cpa_df[cpa_df["player"]==top_name]
            src2 = cpa_df[cpa_df["player"]==sel]
            if len(comp) > 0 and len(src2) > 0:
                rcols = ["cpa_xG_p90","cpa_xA_p90","cpa_xGChain_p90","cpa_xGBuildup_p90",
                         "role_burden","shots_p90","key_passes_p90"]
                rcols = [c for c in rcols if c in cpa_df.columns]
                if rcols:
                    labels = [c.replace("cpa_","").replace("_p90","").replace("_"," ").title() for c in rcols]
                    v1 = [(cpa_df[c] <= src2.iloc[0][c]).mean()*100 for c in rcols]
                    v2 = [(cpa_df[c] <= comp.iloc[0][c]).mean()*100 for c in rcols]
                    fig = go.Figure()
                    fig.add_trace(go.Scatterpolar(r=v1+[v1[0]], theta=labels+[labels[0]],
                                                   fill="toself", name=sel, line_color="#FF6B35"))
                    fig.add_trace(go.Scatterpolar(r=v2+[v2[0]], theta=labels+[labels[0]],
                                                   fill="toself", name=top_name, line_color="#4ECDC4"))
                    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0,100])),
                                      title="Radar: " + sel + " vs " + top_name, height=500)
                    st.plotly_chart(fig, use_container_width=True)
""")

# ============================================================
# Ecosystems
# ============================================================
write("pages/pg_ecosystems.py", """\
import streamlit as st
import pandas as pd
import plotly.express as px
import pathlib
from glossary import show_glossary, fmt_value

st.title("Team Ecosystem Profiles")
st.caption("xGD, squad value, goal concentration, threat corridors")
show_glossary()

SD = pathlib.Path("scraped_data")

@st.cache_data
def load():
    for f in ["engine_team_ecosystems_v3.csv","engine_team_ecosystems.csv"]:
        p = SD / f
        if p.exists():
            return pd.read_csv(p)
    return None

eco = load()
if eco is None:
    st.error("Ecosystem data not found.")
    st.stop()

if "league" in eco.columns:
    sel = st.selectbox("League", ["All"] + sorted(eco["league"].unique().tolist()), key="eco_l")
    fdf = eco if sel == "All" else eco[eco["league"]==sel]
else:
    fdf = eco

xgd = "xGD" if "xGD" in fdf.columns else None
ppg = "ppg" if "ppg" in fdf.columns else None

if xgd and ppg:
    fig = px.scatter(fdf, x=xgd, y=ppg, hover_name="team",
                     color="league" if "league" in fdf.columns else None,
                     size="squad_value" if "squad_value" in fdf.columns else None,
                     size_max=20, opacity=0.8, title="Ecosystem Map (size = squad value)")
    fig.update_layout(height=550)
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Full Data")
show = [c for c in fdf.columns if c != "threat_corridors"]
st.dataframe(fdf[show].sort_values(xgd if xgd else fdf.columns[0], ascending=False).reset_index(drop=True),
             use_container_width=True, height=600)
""")

# ============================================================
# Adversity
# ============================================================
write("pages/pg_adversity.py", """\
import streamlit as st
import pandas as pd
import plotly.express as px
import pathlib
from glossary import show_glossary, sidebar_filters

st.title("Adversity and Resilience Profiles")
st.caption("Pressure performance | Big-game ratios | Position-filtered")
show_glossary()

SD = pathlib.Path("scraped_data")

@st.cache_data
def load():
    return pd.read_csv(SD / "engine_cpa_profiles.csv") if (SD / "engine_cpa_profiles.csv").exists() else None

df = load()
if df is None:
    st.error("Data not found.")
    st.stop()

fdf = sidebar_filters(df, prefix="adv")

adv_col = "resilience_ratio" if "resilience_ratio" in fdf.columns else None
bg_col = "big_game_ratio" if "big_game_ratio" in fdf.columns else None

if adv_col and bg_col:
    st.subheader("Resilience vs Big-Game Ratio (" + str(len(fdf)) + " players)")
    fig = px.scatter(fdf, x=adv_col, y=bg_col, hover_name="player",
                     color="position_band" if "position_band" in fdf.columns else "league",
                     opacity=0.7, title="Who thrives under pressure?")
    fig.update_layout(height=550)
    st.plotly_chart(fig, use_container_width=True)

sort_col = "position_score" if "position_score" in fdf.columns else "cpa_xGI_p90"
show = ["player","team","position_group","archetype","age_bracket","reliability_tier",
        "position_score","position_pctile","resilience_ratio","big_game_ratio","total_minutes"]
show = [c for c in show if c in fdf.columns]
st.dataframe(fdf.nlargest(50, sort_col)[show].reset_index(drop=True), use_container_width=True, height=600)
""")

# ============================================================
# Transfer Intelligence
# ============================================================
write("pages/pg_transfer.py", """\
import streamlit as st
import pandas as pd
import plotly.express as px
import pathlib
from glossary import show_glossary, sidebar_filters, fmt_value

st.title("Transfer Intelligence")
st.caption("Position-weighted T-Score | Financial feasibility | Discount scoring")
show_glossary()

SD = pathlib.Path("scraped_data")

@st.cache_data
def load():
    return pd.read_csv(SD / "engine_cpa_profiles.csv") if (SD / "engine_cpa_profiles.csv").exists() else None

df = load()
if df is None:
    st.error("Data not found.")
    st.stop()

fdf = sidebar_filters(df, prefix="ti")

st.subheader("Value Map (" + str(len(fdf)) + " players)")
if "position_pctile" in fdf.columns and "value_eur" in fdf.columns:
    plot_df = fdf[fdf["value_eur"].notna() & (fdf["value_eur"] > 0)].copy()
    if len(plot_df) > 0:
        fig = px.scatter(plot_df, x="value_eur", y="position_pctile", hover_name="player",
                         color="position_band" if "position_band" in plot_df.columns else "league",
                         opacity=0.7, log_x=True,
                         title="Position Percentile vs Market Value (log scale)")
        fig.update_layout(height=550, xaxis_title="Market Value (EUR, log)", yaxis_title="Position Percentile")
        st.plotly_chart(fig, use_container_width=True)

st.subheader("Best Value Targets (Discount Score)")
show = ["player","team","league","position_group","archetype","age_bracket",
        "position_score","position_pctile","discount_score","overall_rating",
        "value_eur","potential","reliability_tier"]
show = [c for c in show if c in fdf.columns]
sort_col = "discount_score" if "discount_score" in fdf.columns else "position_score"
disp = fdf[fdf["position_band"] != "Goalkeeper"].nlargest(50, sort_col)[show].reset_index(drop=True)
disp.index = disp.index + 1
st.dataframe(disp, use_container_width=True, height=600)
""")

# ============================================================
# GK Profiles
# ============================================================
write("pages/pg_gk.py", """\
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import pathlib
from glossary import show_glossary

st.title("Goalkeeper Profiles")
st.caption("Dedicated GK track | SoFIFA GK attributes")
show_glossary()

SD = pathlib.Path("scraped_data")

@st.cache_data
def load():
    gp = SD / "engine_gk_profiles.csv"
    gs = SD / "engine_gk_similarity.csv"
    return (pd.read_csv(gp) if gp.exists() else None,
            pd.read_csv(gs) if gs.exists() else None)

gk, gk_sim = load()
if gk is None:
    st.warning("GK profiles not found.")
    st.stop()

hide = ["player_id","understat_id"]
show = [c for c in gk.columns if c not in hide]
st.dataframe(gk[show].reset_index(drop=True), use_container_width=True, height=500)

if gk_sim is not None and "player" in gk_sim.columns:
    st.divider()
    st.subheader("GK Similarity")
    sel = st.selectbox("Find similar to", sorted(gk_sim["player"].unique().tolist()), key="gk_s")
    gr = gk_sim[gk_sim["player"]==sel]
    if len(gr) > 0:
        sim_names = [c for c in gk_sim.columns if c.startswith("sim_") and c.endswith("_name")]
        results = []
        for nc in sim_names:
            sc = nc.replace("_name","_score")
            if sc in gr.columns and pd.notna(gr.iloc[0][nc]):
                results.append({"Goalkeeper": gr.iloc[0][nc], "Similarity": round(float(gr.iloc[0][sc]),4)})
        if results:
            st.dataframe(pd.DataFrame(results), use_container_width=True)
""")

# ============================================================
# Shortlist
# ============================================================
write("pages/pg_shortlist.py", """\
import streamlit as st
import pandas as pd
import plotly.express as px
import pathlib
from glossary import show_glossary, sidebar_filters, fmt_value

st.title("Scouting Shortlist Builder")
st.caption("Multi-filter | Position-weighted | Financial feasibility | CSV export")
show_glossary()

SD = pathlib.Path("scraped_data")

@st.cache_data
def load():
    return pd.read_csv(SD / "engine_cpa_profiles.csv") if (SD / "engine_cpa_profiles.csv").exists() else None

df = load()
if df is None:
    st.error("Data not found.")
    st.stop()

fdf = sidebar_filters(df, prefix="sl")

st.subheader("Shortlist: " + str(len(fdf)) + " players")
sort_opts = [c for c in ["position_score","position_pctile","discount_score",
             "cpa_xGI_p90","overall_rating"] if c in fdf.columns]
sort_by = st.selectbox("Sort by", sort_opts, key="sl_sort")

show = ["player","team","league","position_group","archetype","age_bracket",
        "reliability_tier","position_score","position_pctile","cpa_xGI_p90",
        "overall_rating","value_eur","discount_score","total_minutes"]
show = [c for c in show if c in fdf.columns]
display = fdf.nlargest(100, sort_by)[show].reset_index(drop=True)
display.index = display.index + 1
st.dataframe(display, use_container_width=True, height=600)

st.divider()
st.subheader("Visual Map")
y_opts = [c for c in ["position_pctile","resilience_ratio","discount_score"] if c in fdf.columns]
if y_opts and "cpa_xGI_p90" in fdf.columns and len(fdf) > 1:
    y_col = st.selectbox("Y-axis", y_opts, key="sl_y")
    color_c = "position_band" if "position_band" in fdf.columns else "archetype"
    fig = px.scatter(fdf, x="cpa_xGI_p90", y=y_col, hover_name="player",
                     color=color_c, opacity=0.7, title="Shortlist Map")
    fig.update_layout(height=500)
    st.plotly_chart(fig, use_container_width=True)

st.divider()
csv = display.to_csv(index=False)
st.download_button("Download Shortlist CSV", csv, "scouting_shortlist.csv", "text/csv")
""")

# ============================================================
# Team Targeting (complete rewrite with financial feasibility)
# ============================================================
write("pages/pg_team_targeting.py", """\
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
""")

# ============================================================
# Add __init__.py to pages for glossary import
# ============================================================
write("pages/__init__.py", """\
# This file allows glossary.py to be imported from pages/
""")

print()
print("=" * 60)
print("Part 2 complete: " + str(count) + " files written")
print("=" * 60)
print()
print("Now run:")
print("  streamlit run dashboard_v2.py")
