import streamlit as st
import pandas as pd
import plotly.express as px

st.title("Adversity and Resilience Profiles")
D = "scraped_data"

@st.cache_data
def load():
    return pd.read_csv("{}/engine_adversity.csv".format(D))

df = load()

col1, col2 = st.columns(2)
with col1:
    leagues = ["All"] + sorted(df["league"].dropna().unique().tolist())
    sel_lg = st.selectbox("League", leagues)
with col2:
    top_n = st.slider("Show Top N", 10, 100, 30)

fdf = df if sel_lg == "All" else df[df["league"]==sel_lg]

if "adversity_score" in fdf.columns:
    st.subheader("Top {} Pressure Players".format(top_n))
    top = fdf.nlargest(top_n, "adversity_score")
    show_cols = ["player","team","league","archetype","adversity_score","adversity_rank",
                 "resilience_ratio","big_game_ratio","xG_p90","cpa_xGI_p90"]
    avail = [c for c in show_cols if c in top.columns]
    st.dataframe(top[avail], use_container_width=True, hide_index=True)

    if "resilience_ratio" in fdf.columns and "big_game_ratio" in fdf.columns:
        fig = px.scatter(fdf, x="resilience_ratio", y="big_game_ratio",
                         hover_name="player", color="league" if sel_lg=="All" else "archetype",
                         opacity=0.6, title="Resilience vs Big-Game Performance")
        fig.add_vline(x=1.0, line_dash="dash", line_color="gray")
        fig.add_hline(y=1.0, line_dash="dash", line_color="gray")
        fig.update_layout(height=550)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("Players in the top-right quadrant maintain or exceed their baseline output "
                    "both when trailing and against elite defenses. These are the players who rise under adversity.")
