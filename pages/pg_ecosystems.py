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
