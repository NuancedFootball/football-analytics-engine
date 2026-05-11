import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import pathlib

st.title("Player Profiles (CPA-Adjusted)")
st.caption("Contextual Performance Adjustment: LDI + OQA + RBI normalization")

SD = pathlib.Path("scraped_data")

@st.cache_data
def load_cpa():
    p = SD / "engine_cpa_profiles.csv"
    return pd.read_csv(p) if p.exists() else None

df = load_cpa()
if df is None:
    st.error("engine_cpa_profiles.csv not found.")
    st.stop()

# --- Detect the minutes column name ---
min_col = None
for candidate in ["minutes","total_minutes","mins","min","Minutes"]:
    if candidate in df.columns:
        min_col = candidate
        break

# --- Detect the matches column name ---
match_col = None
for candidate in ["matches","match_count","games","total_matches","n_matches"]:
    if candidate in df.columns:
        match_col = candidate
        break

with st.sidebar:
    st.subheader("Filters")
    leagues = ["All"] + sorted(df["league"].unique().tolist()) if "league" in df.columns else ["All"]
    sel_league = st.selectbox("League", leagues, key="cpa_lg")
    if "archetype" in df.columns:
        archs = ["All"] + sorted(df["archetype"].dropna().unique().tolist())
        sel_arch = st.selectbox("Archetype", archs, key="cpa_ar")
    else:
        sel_arch = "All"
    max_min_val = int(df[min_col].max()) if min_col else 3000
    min_mins = st.slider("Min Minutes", 450, min(3000, max_min_val), 900, step=90, key="cpa_mm")

fdf = df.copy()
if sel_league != "All":
    fdf = fdf[fdf["league"] == sel_league]
if sel_arch != "All" and "archetype" in fdf.columns:
    fdf = fdf[fdf["archetype"] == sel_arch]
if min_col:
    fdf = fdf[fdf[min_col] >= min_mins]

st.subheader("Leaderboard (" + str(len(fdf)) + " players)")
sort_options = [c for c in ["cpa_xGI_p90","cpa_xG_p90","cpa_xA_p90","role_burden"] if c in fdf.columns]
if min_col:
    sort_options.append(min_col)
sort_col = st.selectbox("Sort by", sort_options, key="cpa_s") if sort_options else fdf.columns[0]

display_cols = ["player","team","league","archetype","cpa_xGI_p90","cpa_xG_p90",
                "cpa_xA_p90","role_burden"]
if min_col:
    display_cols.append(min_col)
if match_col:
    display_cols.append(match_col)
display_cols = [c for c in display_cols if c in fdf.columns]
st.dataframe(fdf.nlargest(50, sort_col)[display_cols].reset_index(drop=True),
             width="stretch", height=600)

st.divider()
st.subheader("Player Radar")
player_list = sorted(fdf["player"].unique().tolist())
if player_list:
    sel_p = st.selectbox("Select Player", player_list, key="cpa_rp")
    row = fdf[fdf["player"] == sel_p].iloc[0]

    radar_cols = ["cpa_xG_p90","cpa_xA_p90","cpa_xGChain_p90","cpa_xGBuildup_p90",
                  "role_burden","shots_p90","key_passes_p90","goals_p90","assists_p90"]
    radar_cols = [c for c in radar_cols if c in fdf.columns]

    if radar_cols:
        vals = []
        for c in radar_cols:
            pctl = (fdf[c] <= row[c]).mean()
            vals.append(round(pctl * 100, 1))

        labels = [c.replace("cpa_","").replace("_p90","").replace("_"," ").title()
                  for c in radar_cols]

        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=vals + [vals[0]],
            theta=labels + [labels[0]],
            fill="toself", name=sel_p, line_color="#FF6B35"
        ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            showlegend=False,
            title=sel_p + " - Percentile Radar (vs " + str(len(fdf)) + " players)",
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("CPA xGI/90", round(row.get("cpa_xGI_p90", 0), 3))
        c2.metric("League", str(row.get("league", "?")))
        c3.metric("Role Burden", round(row.get("role_burden", 0), 3))
        if min_col:
            c4.metric("Minutes", int(row.get(min_col, 0)))
        else:
            c4.metric("Minutes", "N/A")
