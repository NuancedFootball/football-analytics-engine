import streamlit as st
import pandas as pd
import plotly.express as px

st.title("Team Ecosystem Profiles")
D = "scraped_data"

@st.cache_data
def load():
    return pd.read_csv(f"{D}/engine_team_ecosystems_v3.csv")

@st.cache_data
def load_cpa():
    return pd.read_csv(f"{D}/engine_cpa_profiles.csv")

eco = load()
cpa = load_cpa()

league = st.selectbox("League", ["All"] + sorted(eco["league"].unique()))
if league != "All":
    eco = eco[eco["league"]==league]

st.header("League Table by xGD")
cols = ["team","league","matches","wins","draws","losses","ppg",
        "goals_for","goals_against","xGF","xGA","xGD",
        "goal_concentration","creativity_concentration","n_archetypes"]
st.dataframe(eco[cols].sort_values("xGD", ascending=False), use_container_width=True, hide_index=True)

st.header("xGD vs Points Per Game")
fig = px.scatter(eco, x="xGD", y="ppg", color="league", hover_data=["team"],
                 size="matches", title="Expected vs Actual Performance", height=500)
st.plotly_chart(fig, use_container_width=True)

st.header("Concentration Analysis")
st.markdown("*Higher = more dependent on fewer players. Lower = more distributed.*")
fig2 = px.scatter(eco, x="goal_concentration", y="creativity_concentration",
                  color="league", hover_data=["team","ppg","xGD"],
                  title="Goal vs Creativity Concentration (Herfindahl Index)", height=500)
st.plotly_chart(fig2, use_container_width=True)

st.header("Team Deep Dive")
team = st.selectbox("Select Team", eco.sort_values("xGD", ascending=False)["team"].unique())
te = eco[eco["team"]==team].iloc[0]

c1,c2,c3,c4 = st.columns(4)
c1.metric("PPG", te["ppg"])
c2.metric("xGD", f"{te['xGD']:+.1f}")
c3.metric("Archetypes", int(te["n_archetypes"]))
c4.metric("Resilience", f"{te['avg_resilience']:.3f}")

st.markdown(f"**Threat Corridors:** {te.get('threat_corridors','')}")

st.subheader(f"{team} Squad")
squad = cpa[cpa["team"]==team].sort_values("cpa_xGI_p90", ascending=False)
st.dataframe(squad[["player","position","archetype","matches","total_minutes",
                     "cpa_xGI_p90","xG_p90","xA_p90","role_burden","resilience_ratio"]],
             use_container_width=True, hide_index=True)
