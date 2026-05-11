import streamlit as st
import pandas as pd
import plotly.express as px

st.title("Team Ecosystem Profiles")
D = "scraped_data"

@st.cache_data
def load():
    return pd.read_csv("{}/engine_team_ecosystems_v3.csv".format(D))

df = load()

col1, col2 = st.columns(2)
with col1:
    leagues = ["All"] + sorted(df["league"].dropna().unique().tolist())
    sel_lg = st.selectbox("League", leagues)
with col2:
    metric = st.selectbox("Color by", ["xGD","ppg","creativity_concentration","goal_concentration","avg_resilience"])

fdf = df if sel_lg == "All" else df[df["league"]==sel_lg]

st.subheader("Team Landscape")
fig = px.scatter(fdf, x="xGF", y="xGA", color=metric, hover_name="team",
                 size="matches", text="team", size_max=20,
                 color_continuous_scale="RdYlGn")
fig.update_traces(textposition="top center", textfont_size=9)
fig.update_layout(height=600)
st.plotly_chart(fig, use_container_width=True)

st.subheader("Concentration Indices")
conc_cols = ["team","league","creativity_concentration","goal_concentration","buildup_concentration"]
avail = [c for c in conc_cols if c in fdf.columns]
st.dataframe(fdf[avail].sort_values("goal_concentration", ascending=False), use_container_width=True, hide_index=True)

st.subheader("Team Deep Dive")
sel_tm = st.selectbox("Select Team", sorted(fdf["team"].unique()))
if sel_tm:
    tr = fdf[fdf["team"]==sel_tm].iloc[0]
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("PPG", "{:.2f}".format(tr["ppg"]))
    c2.metric("xGD", "{:+.2f}".format(tr["xGD"]))
    c3.metric("Goal Conc.", "{:.3f}".format(tr["goal_concentration"]))
    c4.metric("Archetypes", "{}".format(tr.get("n_archetypes",0)))
    st.markdown("Threat Corridors: {}".format(tr.get("threat_corridors","N/A")))
