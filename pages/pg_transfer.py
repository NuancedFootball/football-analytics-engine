import streamlit as st
import pandas as pd
import plotly.express as px
import pathlib

st.title("Transfer Intelligence")
st.caption("Composite T-Score: output efficiency + growth + adversity + fit")

SD = pathlib.Path("scraped_data")

@st.cache_data
def load():
    p = SD / "engine_transfer_intel.csv"
    return pd.read_csv(p) if p.exists() else None

ti = load()
if ti is None:
    st.error("Transfer intel data not found.")
    st.stop()

ts = None
for c in ["transfer_score","t_score"]:
    if c in ti.columns:
        ts = c
        break

min_col = None
for c in ["minutes","total_minutes","mins"]:
    if c in ti.columns:
        min_col = c
        break

with st.sidebar:
    if "league" in ti.columns:
        sel_l = st.selectbox("League", ["All"] + sorted(ti["league"].unique().tolist()), key="ti_l")
    else:
        sel_l = "All"
    if "archetype" in ti.columns:
        sel_a = st.selectbox("Archetype", ["All"] + sorted(ti["archetype"].dropna().unique().tolist()), key="ti_a")
    else:
        sel_a = "All"
    min_m = st.slider("Min Minutes", 450, 3000, 900, step=90, key="ti_m")

fdf = ti.copy()
if sel_l != "All" and "league" in fdf.columns:
    fdf = fdf[fdf["league"] == sel_l]
if sel_a != "All" and "archetype" in fdf.columns:
    fdf = fdf[fdf["archetype"] == sel_a]
if min_col:
    fdf = fdf[fdf[min_col] >= min_m]

cpa_col = "cpa_xGI_p90" if "cpa_xGI_p90" in fdf.columns else None

if ts and cpa_col:
    st.subheader("T-Score vs CPA Output")
    color = "archetype" if "archetype" in fdf.columns else ("league" if "league" in fdf.columns else None)
    fig = px.scatter(fdf, x=cpa_col, y=ts, hover_name="player",
                     color=color, opacity=0.7, title="Transfer Intelligence Map")
    fig.update_layout(height=550)
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Transfer Targets (" + str(len(fdf)) + " players)")
show = ["player","team","league","archetype"]
if ts: show.append(ts)
if cpa_col: show.append(cpa_col)
eff = "output_efficiency" if "output_efficiency" in fdf.columns else None
if eff: show.append(eff)
if min_col: show.append(min_col)
match_col = None
for mc in ["matches","match_count","games"]:
    if mc in fdf.columns:
        match_col = mc
        break
if match_col: show.append(match_col)
show = [c for c in show if c in fdf.columns]

if ts:
    st.dataframe(fdf.nlargest(50, ts)[show].reset_index(drop=True),
                 use_container_width=True, height=600)
