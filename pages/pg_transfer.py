import streamlit as st
import pandas as pd
import plotly.express as px
import pathlib
from glossary import show_glossary, sidebar_filters, fmt_value

st.title("Transfer Intelligence")
st.caption("Position-weighted T-Score | Financial feasibility | Discount scoring")
show_glossary()

SD = pathlib.Path("scraped_data")

@st.cache_data
def load():
    return pd.read_csv(SD / "engine_cpa_profiles.csv") if (SD / "engine_cpa_profiles.csv").exists() else None

df = load()
if df is None:
    st.error("Data not found.")
    st.stop()

fdf = sidebar_filters(df, prefix="ti")

st.subheader("Value Map (" + str(len(fdf)) + " players)")
if "position_pctile" in fdf.columns and "value_eur" in fdf.columns:
    plot_df = fdf[fdf["value_eur"].notna() & (fdf["value_eur"] > 0)].copy()
    if len(plot_df) > 0:
        fig = px.scatter(plot_df, x="value_eur", y="position_pctile", hover_name="player",
                         color="position_band" if "position_band" in plot_df.columns else "league",
                         opacity=0.7, log_x=True,
                         title="Position Percentile vs Market Value (log scale)")
        fig.update_layout(height=550, xaxis_title="Market Value (EUR, log)", yaxis_title="Position Percentile")
        st.plotly_chart(fig, use_container_width=True)

st.subheader("Best Value Targets (Discount Score)")
show = ["player","team","league","position_group","archetype","age_bracket",
        "position_score","position_pctile","discount_score","overall_rating",
        "value_eur","potential","reliability_tier"]
show = [c for c in show if c in fdf.columns]
sort_col = "discount_score" if "discount_score" in fdf.columns else "position_score"
disp = fdf[fdf["position_band"] != "Goalkeeper"].nlargest(50, sort_col)[show].reset_index(drop=True)
disp.index = disp.index + 1
st.dataframe(disp, use_container_width=True, height=600)
