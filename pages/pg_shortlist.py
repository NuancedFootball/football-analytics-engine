import streamlit as st
import pandas as pd
import plotly.express as px
import pathlib

st.title("Scouting Shortlist Builder")
st.caption("Filter, rank, and export targets across all engine dimensions")

SD = pathlib.Path("scraped_data")

@st.cache_data
def load_all():
    data = {}
    for name in ["engine_cpa_profiles.csv","engine_adversity.csv",
                 "engine_transfer_intel.csv"]:
        p = SD / name
        if p.exists():
            data[name] = pd.read_csv(p)
    return data

data = load_all()
cpa = data.get("engine_cpa_profiles.csv")
adv = data.get("engine_adversity.csv")
ti  = data.get("engine_transfer_intel.csv")

if cpa is None:
    st.error("CPA profiles required.")
    st.stop()

# Detect column names
min_col = None
for c in ["minutes","total_minutes","mins"]:
    if c in cpa.columns:
        min_col = c
        break
match_col = None
for mc in ["matches","match_count","games"]:
    if mc in cpa.columns:
        match_col = mc
        break

df = cpa.copy()
if adv is not None and "player" in adv.columns:
    adv_extra = [c for c in adv.columns if c not in cpa.columns]
    df = df.merge(adv[["player"] + adv_extra], on="player", how="left")
if ti is not None and "player" in ti.columns:
    ti_extra = [c for c in ti.columns if c not in df.columns]
    df = df.merge(ti[["player"] + ti_extra], on="player", how="left")

with st.sidebar:
    st.subheader("Shortlist Filters")
    if "league" in df.columns:
        sel_leagues = st.multiselect("Leagues", sorted(df["league"].unique().tolist()),
                                     default=sorted(df["league"].unique().tolist()),
                                     key="sl_lg")
    else:
        sel_leagues = None

    if "archetype" in df.columns:
        all_archs = sorted(df["archetype"].dropna().unique().tolist())
        sel_archs = st.multiselect("Archetypes", all_archs, default=all_archs, key="sl_ar")
    else:
        sel_archs = None

    min_mins = st.slider("Min Minutes", 450, 3000, 900, step=90, key="sl_mm")
    min_xgi = st.slider("Min CPA xGI/90", 0.0, 1.5, 0.0, step=0.05, key="sl_xgi")

    ts_col = None
    for tc in ["transfer_score","t_score"]:
        if tc in df.columns:
            ts_col = tc
            break
    if ts_col:
        min_ts = st.slider("Min T-Score", 0.0, 3.0, 0.0, step=0.1, key="sl_ts")
    else:
        min_ts = 0.0

fdf = df.copy()
if sel_leagues:
    fdf = fdf[fdf["league"].isin(sel_leagues)]
if sel_archs and "archetype" in fdf.columns:
    fdf = fdf[fdf["archetype"].isin(sel_archs)]
if min_col:
    fdf = fdf[fdf[min_col] >= min_mins]
if "cpa_xGI_p90" in fdf.columns:
    fdf = fdf[fdf["cpa_xGI_p90"] >= min_xgi]
if ts_col and min_ts > 0:
    fdf = fdf[fdf[ts_col] >= min_ts]

st.subheader("Shortlist: " + str(len(fdf)) + " players match filters")

sort_opts = ["cpa_xGI_p90"]
if ts_col:
    sort_opts.append(ts_col)
sort_opts += [c for c in ["role_burden","adversity_composite","resilience_ratio"] if c in fdf.columns]
if min_col:
    sort_opts.append(min_col)
sort_by = st.selectbox("Sort by", sort_opts, key="sl_sort")

show = ["player","team","league","archetype","cpa_xGI_p90","cpa_xG_p90",
        "cpa_xA_p90","role_burden"]
if ts_col: show.append(ts_col)
show += [c for c in ["adversity_composite","resilience_ratio"] if c in fdf.columns]
if min_col: show.append(min_col)
if match_col: show.append(match_col)
show = [c for c in show if c in fdf.columns]

display = fdf.nlargest(100, sort_by)[show].reset_index(drop=True)
display.index = display.index + 1
st.dataframe(display, use_container_width=True, height=600)

st.divider()
st.subheader("Visual Map")
y_opts = [c for c in ["resilience_ratio","role_burden","adversity_composite"]
          if c in fdf.columns]
if y_opts and "cpa_xGI_p90" in fdf.columns and len(fdf) > 1:
    y_col = st.selectbox("Y-axis", y_opts, key="sl_y")
    color_c = "archetype" if "archetype" in fdf.columns else (
              "league" if "league" in fdf.columns else None)
    kw = dict(x="cpa_xGI_p90", y=y_col, hover_name="player", opacity=0.7,
              title="Shortlist Map")
    if color_c:
        kw["color"] = color_c
    if match_col and fdf[match_col].notna().sum() > 0:
        kw["size"] = match_col
        kw["size_max"] = 15
    fig = px.scatter(fdf, **kw)
    fig.update_layout(height=500)
    st.plotly_chart(fig, use_container_width=True)

st.divider()
csv = display.to_csv(index=False)
st.download_button("Download Shortlist CSV", csv,
                   "scouting_shortlist.csv", "text/csv")
