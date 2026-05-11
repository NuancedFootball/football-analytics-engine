import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.title("CPA-Adjusted Player Profiles")
D = "scraped_data"

@st.cache_data
def load():
    return pd.read_csv("{}/engine_cpa_profiles.csv".format(D))

df = load()

col1, col2, col3 = st.columns(3)
with col1:
    leagues = ["All"] + sorted(df["league"].dropna().unique().tolist())
    sel_lg = st.selectbox("League", leagues)
with col2:
    min_mins = st.slider("Min Minutes", 450, 3000, 900, 90)
with col3:
    positions = ["All"] + sorted(df["position"].dropna().unique().tolist())
    sel_pos = st.selectbox("Position Filter", positions)

fdf = df[df["total_minutes"] >= min_mins].copy()
if sel_lg != "All":
    fdf = fdf[fdf["league"] == sel_lg]
if sel_pos != "All":
    fdf = fdf[fdf["position"].str.contains(sel_pos, na=False)]

st.subheader("{} qualified players".format(len(fdf)))
metric = st.selectbox("Rank by", [
    "cpa_xGI_p90", "cpa_xG_p90", "cpa_xA_p90", "goal_involvement_p90",
    "xG_overperf_p90", "role_burden", "resilience_ratio", "big_game_ratio",
])
show_cols = ["player","team","league","position","matches","total_minutes",
             "cpa_xG_p90","cpa_xA_p90","cpa_xGI_p90","xG_overperf_p90",
             "role_burden","resilience_ratio","big_game_ratio"]
avail = [c for c in show_cols if c in fdf.columns]
st.dataframe(fdf[avail].sort_values(metric, ascending=False).head(50),
             use_container_width=True, hide_index=True, height=600)

st.subheader("CPA Scatter")
num_cols = [c for c in fdf.columns if fdf[c].dtype in ["float64","int64"]]
c1, c2 = st.columns(2)
with c1:
    x_ax = st.selectbox("X axis", num_cols, index=num_cols.index("cpa_xG_p90") if "cpa_xG_p90" in num_cols else 0)
with c2:
    y_ax = st.selectbox("Y axis", num_cols, index=num_cols.index("cpa_xA_p90") if "cpa_xA_p90" in num_cols else 1)

color_col = "league" if sel_lg == "All" else "team"
fig = px.scatter(fdf, x=x_ax, y=y_ax, hover_name="player", color=color_col,
                 size="total_minutes", size_max=15, opacity=0.7)
fig.update_layout(height=550)
st.plotly_chart(fig, use_container_width=True)

st.subheader("Player Deep Dive")
sel_player = st.selectbox("Select Player", sorted(fdf["player"].unique()))
if sel_player:
    pr = fdf[fdf["player"]==sel_player].iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("CPA xGI/90", "{:.3f}".format(pr.get("cpa_xGI_p90", 0)))
    c2.metric("Role Burden", "{:.3f}".format(pr.get("role_burden", 0)))
    c3.metric("Resilience", "{:.3f}".format(pr.get("resilience_ratio", 0)))
    c4.metric("Big Game", "{:.3f}".format(pr.get("big_game_ratio", 0)))

    radar_cols = ["cpa_xG_p90","cpa_xA_p90","shots_p90","key_passes_p90","xGChain_p90","xGBuildup_p90","role_burden"]
    radar_avail = [c for c in radar_cols if c in fdf.columns]
    if radar_avail:
        vals = []
        for c in radar_avail:
            col_max = fdf[c].quantile(0.95)
            vals.append(min(pr.get(c, 0) / max(col_max, 0.001), 1.5))
        fig_r = go.Figure()
        fig_r.add_trace(go.Scatterpolar(r=vals + [vals[0]], theta=radar_avail + [radar_avail[0]],
                                         fill="toself", name=sel_player, line=dict(color="#00d4ff")))
        fig_r.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 1.5])),
                            title="Radar: {}".format(sel_player), height=450)
        st.plotly_chart(fig_r, use_container_width=True)
