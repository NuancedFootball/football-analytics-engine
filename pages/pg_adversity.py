import streamlit as st
import pandas as pd
import plotly.express as px
import pathlib

st.title("Adversity and Resilience Profiles")
st.caption("Pressure-match performance, big-game ratios, composure indices")

SD = pathlib.Path("scraped_data")

@st.cache_data
def load():
    p = SD / "engine_adversity.csv"
    return pd.read_csv(p) if p.exists() else None

adv = load()
if adv is None:
    st.error("Adversity data not found.")
    st.stop()

# Detect column names
adv_col = None
for c in ["adversity_composite","adversity_score"]:
    if c in adv.columns:
        adv_col = c
        break
res_col = "resilience_ratio" if "resilience_ratio" in adv.columns else None
big_col = "big_game_ratio" if "big_game_ratio" in adv.columns else None

min_col = None
for c in ["minutes","total_minutes","mins"]:
    if c in adv.columns:
        min_col = c
        break

with st.sidebar:
    if "league" in adv.columns:
        leagues = ["All"] + sorted(adv["league"].unique().tolist())
        sel_l = st.selectbox("League", leagues, key="adv_l")
    else:
        sel_l = "All"
    min_m = st.slider("Min Minutes", 450, 3000, 900, step=90, key="adv_m")

fdf = adv.copy()
if sel_l != "All" and "league" in fdf.columns:
    fdf = fdf[fdf["league"] == sel_l]
if min_col:
    fdf = fdf[fdf[min_col] >= min_m]

if adv_col and res_col and res_col in fdf.columns:
    st.subheader("Adversity vs Resilience")
    fig = px.scatter(fdf, x=adv_col, y=res_col, hover_name="player",
                     color="league" if "league" in fdf.columns else None,
                     opacity=0.7, title="Who thrives under pressure?")
    fig.update_layout(height=550)
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Pressure Player Rankings (" + str(len(fdf)) + " players)")
sort_opts = [c for c in [adv_col, res_col, big_col] if c and c in fdf.columns]
sort_by = st.selectbox("Sort by", sort_opts, key="adv_s") if sort_opts else fdf.columns[0]
show = ["player","team","league"]
show += [c for c in [adv_col, res_col, big_col] if c and c in fdf.columns]
if min_col: show.append(min_col)
match_col = None
for mc in ["matches","match_count","games"]:
    if mc in fdf.columns:
        match_col = mc
        break
if match_col: show.append(match_col)
st.dataframe(fdf.nlargest(50, sort_by)[show].reset_index(drop=True),
             use_container_width=True, height=600)
