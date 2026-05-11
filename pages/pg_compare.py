import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import pathlib

st.title("Head-to-Head Player Comparison")
st.caption("Side-by-side CPA profiles with percentile radars")

SD = pathlib.Path("scraped_data")

@st.cache_data
def load():
    p = SD / "engine_cpa_profiles.csv"
    return pd.read_csv(p) if p.exists() else None

df = load()
if df is None:
    st.error("CPA profiles not found.")
    st.stop()

players = sorted(df["player"].unique().tolist())
col1, col2 = st.columns(2)
with col1:
    p1 = st.selectbox("Player A", players, index=0, key="cmp_a")
with col2:
    p2 = st.selectbox("Player B", players, index=min(1, len(players)-1), key="cmp_b")

r1 = df[df["player"] == p1]
r2 = df[df["player"] == p2]
if len(r1) == 0 or len(r2) == 0:
    st.warning("Select two valid players.")
    st.stop()
r1, r2 = r1.iloc[0], r2.iloc[0]

c1, c2 = st.columns(2)
with c1:
    st.subheader(p1)
    st.write("Team: " + str(r1.get("team","?")) + " | League: " + str(r1.get("league","?")))
    st.write("Archetype: " + str(r1.get("archetype","?")) + " | Minutes: " + str(int(r1.get("minutes",0))))
    st.metric("CPA xGI/90", round(r1.get("cpa_xGI_p90",0), 3))
with c2:
    st.subheader(p2)
    st.write("Team: " + str(r2.get("team","?")) + " | League: " + str(r2.get("league","?")))
    st.write("Archetype: " + str(r2.get("archetype","?")) + " | Minutes: " + str(int(r2.get("minutes",0))))
    st.metric("CPA xGI/90", round(r2.get("cpa_xGI_p90",0), 3))

rcols = ["cpa_xG_p90","cpa_xA_p90","cpa_xGChain_p90","cpa_xGBuildup_p90",
         "role_burden","shots_p90","key_passes_p90","goals_p90","assists_p90"]
rcols = [c for c in rcols if c in df.columns]

if rcols:
    labels = [c.replace("cpa_","").replace("_p90","").replace("_"," ").title()
              for c in rcols]
    v1 = [(df[c] <= r1[c]).mean() * 100 for c in rcols]
    v2 = [(df[c] <= r2[c]).mean() * 100 for c in rcols]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=v1+[v1[0]], theta=labels+[labels[0]],
                                   fill="toself", name=p1, line_color="#FF6B35"))
    fig.add_trace(go.Scatterpolar(r=v2+[v2[0]], theta=labels+[labels[0]],
                                   fill="toself", name=p2, line_color="#4ECDC4"))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0,100])),
                      title="Percentile Radar: " + p1 + " vs " + p2, height=550)
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Stat Comparison")
compare_cols = ["cpa_xGI_p90","cpa_xG_p90","cpa_xA_p90","role_burden",
                "minutes","matches","cpa_xGChain_p90","cpa_xGBuildup_p90",
                "shots_p90","key_passes_p90"]
compare_cols = [c for c in compare_cols if c in df.columns]
comp_data = {"Metric": [], p1: [], p2: []}
for c in compare_cols:
    comp_data["Metric"].append(c.replace("cpa_","").replace("_p90"," /90").replace("_"," ").title())
    v1_val = r1[c]
    v2_val = r2[c]
    comp_data[p1].append(round(v1_val, 3) if isinstance(v1_val, float) else v1_val)
    comp_data[p2].append(round(v2_val, 3) if isinstance(v2_val, float) else v2_val)
st.dataframe(pd.DataFrame(comp_data), use_container_width=True)
