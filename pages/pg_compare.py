import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.title("Head-to-Head Player Comparison")
D = "scraped_data"

@st.cache_data
def load():
    return pd.read_csv("{}/engine_cpa_profiles.csv".format(D))

df = load()
players = sorted(df["player"].unique())

col1, col2 = st.columns(2)
with col1:
    p1 = st.selectbox("Player 1", players, index=0)
with col2:
    p2 = st.selectbox("Player 2", players, index=min(1, len(players)-1))

if p1 and p2 and p1 != p2:
    r1 = df[df["player"]==p1].iloc[0]
    r2 = df[df["player"]==p2].iloc[0]

    st.subheader("Key Metrics")
    metrics = ["cpa_xGI_p90","cpa_xG_p90","cpa_xA_p90","shots_p90","key_passes_p90",
               "role_burden","resilience_ratio","big_game_ratio","xG_overperf_p90"]
    avail = [m for m in metrics if m in df.columns]

    cols = st.columns(min(len(avail), 5))
    for i, m in enumerate(avail[:5]):
        v1 = r1.get(m, 0) or 0
        v2 = r2.get(m, 0) or 0
        delta = v1 - v2
        cols[i].metric(m.replace("_p90","").replace("cpa_",""), "{:.3f}".format(v1),
                       delta="{:+.3f}".format(delta))

    radar_cols = ["cpa_xG_p90","cpa_xA_p90","shots_p90","key_passes_p90","xGChain_p90","xGBuildup_p90","role_burden"]
    radar_avail = [c for c in radar_cols if c in df.columns]
    if radar_avail:
        def normalize(val, col):
            mx = df[col].quantile(0.95)
            return min(val / max(mx, 0.001), 1.5)
        v1s = [normalize(r1.get(c,0) or 0, c) for c in radar_avail]
        v2s = [normalize(r2.get(c,0) or 0, c) for c in radar_avail]
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=v1s+[v1s[0]], theta=radar_avail+[radar_avail[0]],
                                       fill="toself", name=p1, line=dict(color="#00d4ff")))
        fig.add_trace(go.Scatterpolar(r=v2s+[v2s[0]], theta=radar_avail+[radar_avail[0]],
                                       fill="toself", name=p2, line=dict(color="#ff6b6b"), opacity=0.6))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0,1.5])),
                          title="{} vs {}".format(p1, p2), height=500)
        st.plotly_chart(fig, use_container_width=True)
