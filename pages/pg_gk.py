import streamlit as st
import pandas as pd
import plotly.express as px

st.title("Goalkeeper Profiles")
D = "scraped_data"

@st.cache_data
def load():
    return pd.read_csv("{}/gk_season_profiles.csv".format(D))

df = load()

st.subheader("GK Leaderboard")
num_cols = [c for c in df.columns if df[c].dtype in ["float64","int64"]]
sort_col = st.selectbox("Sort by", num_cols)
st.dataframe(df.sort_values(sort_col, ascending=False).head(40), use_container_width=True, hide_index=True)

c1, c2 = st.columns(2)
with c1:
    x_ax = st.selectbox("X axis", num_cols, index=0)
with c2:
    y_ax = st.selectbox("Y axis", num_cols, index=min(1, len(num_cols)-1))

fig = px.scatter(df, x=x_ax, y=y_ax, hover_name="player", text="player",
                 color="league" if "league" in df.columns else None, opacity=0.7)
fig.update_traces(textposition="top center", textfont_size=8)
fig.update_layout(height=550)
st.plotly_chart(fig, use_container_width=True)
