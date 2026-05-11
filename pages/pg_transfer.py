import streamlit as st
import pandas as pd
import plotly.express as px

st.title("Transfer Intelligence")
D = "scraped_data"

@st.cache_data
def load():
    return pd.read_csv("{}/engine_transfer_intel.csv".format(D))

df = load()

col1, col2, col3 = st.columns(3)
with col1:
    leagues = ["All"] + sorted(df["league"].dropna().unique().tolist())
    sel_lg = st.selectbox("League", leagues)
with col2:
    positions = ["All"] + sorted(df["position"].dropna().unique().tolist())
    sel_pos = st.selectbox("Position", positions)
with col3:
    top_n = st.slider("Show Top N", 10, 100, 30)

fdf = df.copy()
if sel_lg != "All":
    fdf = fdf[fdf["league"]==sel_lg]
if sel_pos != "All":
    fdf = fdf[fdf["position"].str.contains(sel_pos, na=False)]

if "transfer_score" in fdf.columns:
    st.subheader("Top {} Transfer Targets".format(top_n))
    top = fdf.nlargest(top_n, "transfer_score")
    show_cols = ["player","team","league","position","transfer_score","transfer_rank",
                 "cpa_xGI_p90","output_efficiency","growth_signal",
                 "resilience_ratio","big_game_ratio"]
    avail = [c for c in show_cols if c in top.columns]
    st.dataframe(top[avail], use_container_width=True, hide_index=True)

    if "output_efficiency" in fdf.columns:
        fig = px.scatter(fdf, x="cpa_xGI_p90", y="output_efficiency",
                         hover_name="player", color="league" if sel_lg=="All" else "position",
                         size="matches", size_max=15, opacity=0.6, title="Output vs Efficiency")
        fig.update_layout(height=550)
        st.plotly_chart(fig, use_container_width=True)
