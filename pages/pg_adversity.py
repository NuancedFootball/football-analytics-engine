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
