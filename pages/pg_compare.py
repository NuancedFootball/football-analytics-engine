import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import pathlib
from glossary import show_glossary, player_card, fmt_value

st.title("Head-to-Head Player Comparison")
st.caption("Side-by-side CPA profiles with SoFIFA attributes and positional radars")

SD = pathlib.Path("scraped_data")

@st.cache_data
def load():
    return pd.read_csv(SD / "engine_cpa_profiles.csv") if (SD / "engine_cpa_profiles.csv").exists() else None

df = load()
if df is None:
    st.error("CPA profiles not found.")
    st.stop()

show_glossary()

players = sorted(df["player"].unique().tolist())
c1, c2 = st.columns(2)
with c1:
    p1 = st.selectbox("Player A", players, index=0, key="cmp_a")
with c2:
    p2 = st.selectbox("Player B", players, index=min(1,len(players)-1), key="cmp_b")

r1 = df[df["player"]==p1]
r2 = df[df["player"]==p2]
if len(r1)==0 or len(r2)==0:
    st.warning("Select two valid players.")
    st.stop()
r1, r2 = r1.iloc[0], r2.iloc[0]

col1, col2 = st.columns(2)
with col1:
    st.subheader(p1)
    player_card(r1)
with col2:
    st.subheader(p2)
    player_card(r2)

# Radar
radar_cols = ["cpa_xG_p90","cpa_xA_p90","cpa_xGChain_p90","cpa_xGBuildup_p90",
              "role_burden","resilience_ratio","big_game_ratio","shots_p90","key_passes_p90"]
radar_cols = [c for c in radar_cols if c in df.columns]

if radar_cols:
    labels = [c.replace("cpa_","").replace("_p90","").replace("_"," ").title() for c in radar_cols]
    v1 = [(df[c] <= r1[c]).mean()*100 for c in radar_cols]
    v2 = [(df[c] <= r2[c]).mean()*100 for c in radar_cols]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=v1+[v1[0]], theta=labels+[labels[0]],
                                   fill="toself", name=p1, line_color="#FF6B35"))
    fig.add_trace(go.Scatterpolar(r=v2+[v2[0]], theta=labels+[labels[0]],
                                   fill="toself", name=p2, line_color="#4ECDC4"))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0,100])),
                      title="Percentile Radar: " + p1 + " vs " + p2, height=550)
    st.plotly_chart(fig, use_container_width=True)

# Stat comparison table
st.subheader("Full Stat Comparison")
compare_cols = ["cpa_xGI_p90","cpa_xG_p90","cpa_xA_p90","position_score","position_pctile",
                "role_burden","resilience_ratio","big_game_ratio","total_minutes","matches",
                "overall_rating","potential","value_eur","age","height_cm"]
compare_cols = [c for c in compare_cols if c in df.columns]
rows = []
for c in compare_cols:
    label = c.replace("cpa_","").replace("_p90"," /90").replace("_"," ").title()
    v1_val = r1[c]
    v2_val = r2[c]
    if c == "value_eur":
        rows.append({"Metric": label, p1: fmt_value(v1_val), p2: fmt_value(v2_val)})
    else:
        rows.append({"Metric": label,
                      p1: round(v1_val,3) if isinstance(v1_val,float) else v1_val,
                      p2: round(v2_val,3) if isinstance(v2_val,float) else v2_val})
st.dataframe(pd.DataFrame(rows), use_container_width=True)
