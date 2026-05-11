import streamlit as st
import pandas as pd
import plotly.express as px
import pathlib

st.title("Team Ecosystem Profiles")
st.caption("xGD, goal concentration, threat corridors, dependency metrics")

SD = pathlib.Path("scraped_data")

@st.cache_data
def load():
    for f in ["engine_team_ecosystems_v3.csv","engine_team_ecosystems_v2.csv",
              "engine_team_ecosystems.csv"]:
        p = SD / f
        if p.exists():
            return pd.read_csv(p)
    return None

eco = load()
if eco is None:
    st.error("Team ecosystem data not found.")
    st.stop()

xgd = "xGD" if "xGD" in eco.columns else ("xgd" if "xgd" in eco.columns else None)
ppg = "ppg" if "ppg" in eco.columns else None

if "league" in eco.columns:
    leagues = ["All"] + sorted(eco["league"].unique().tolist())
    sel = st.selectbox("League", leagues, key="eco_l")
    fdf = eco if sel == "All" else eco[eco["league"] == sel]
else:
    fdf = eco

if xgd and ppg:
    st.subheader("xGD vs Points Per Game")
    color = "league" if "league" in fdf.columns else None
    fig = px.scatter(fdf, x=xgd, y=ppg, hover_name="team",
                     color=color, opacity=0.8, title="Team Ecosystem Map")
    fig.update_layout(height=550)
    st.plotly_chart(fig, use_container_width=True)

gc = None
for candidate in ["goal_conc","goal_concentration"]:
    if candidate in fdf.columns:
        gc = candidate
        break

if gc and xgd:
    st.subheader("Goal Concentration vs xGD")
    fig2 = px.scatter(fdf, x=xgd, y=gc, hover_name="team",
                      color="league" if "league" in fdf.columns else None,
                      title="Higher = more reliant on few scorers")
    fig2.update_layout(height=500)
    st.plotly_chart(fig2, use_container_width=True)

st.subheader("Full Ecosystem Data")
sort_c = xgd if xgd else fdf.columns[0]
st.dataframe(fdf.sort_values(sort_c, ascending=False).reset_index(drop=True),
             use_container_width=True, height=600)
