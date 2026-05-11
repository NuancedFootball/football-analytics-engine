import streamlit as st
import pandas as pd
import plotly.express as px
import pathlib
from glossary import show_glossary, sidebar_filters, fmt_value

st.title("Scouting Shortlist Builder")
st.caption("Multi-filter | Position-weighted | Financial feasibility | CSV export")
show_glossary()

SD = pathlib.Path("scraped_data")

@st.cache_data
def load():
    return pd.read_csv(SD / "engine_cpa_profiles.csv") if (SD / "engine_cpa_profiles.csv").exists() else None

df = load()
if df is None:
    st.error("Data not found.")
    st.stop()

fdf = sidebar_filters(df, prefix="sl")

st.subheader("Shortlist: " + str(len(fdf)) + " players")
sort_opts = [c for c in ["position_score","position_pctile","discount_score",
             "cpa_xGI_p90","overall_rating"] if c in fdf.columns]
sort_by = st.selectbox("Sort by", sort_opts, key="sl_sort")

show = ["player","team","league","position_group","archetype","age_bracket",
        "reliability_tier","position_score","position_pctile","cpa_xGI_p90",
        "overall_rating","value_eur","discount_score","total_minutes"]
show = [c for c in show if c in fdf.columns]
display = fdf.nlargest(100, sort_by)[show].reset_index(drop=True)
display.index = display.index + 1
st.dataframe(display, use_container_width=True, height=600)

st.divider()
st.subheader("Visual Map")
y_opts = [c for c in ["position_pctile","resilience_ratio","discount_score"] if c in fdf.columns]
if y_opts and "cpa_xGI_p90" in fdf.columns and len(fdf) > 1:
    y_col = st.selectbox("Y-axis", y_opts, key="sl_y")
    color_c = "position_band" if "position_band" in fdf.columns else "archetype"
    fig = px.scatter(fdf, x="cpa_xGI_p90", y=y_col, hover_name="player",
                     color=color_c, opacity=0.7, title="Shortlist Map")
    fig.update_layout(height=500)
    st.plotly_chart(fig, use_container_width=True)

st.divider()
csv = display.to_csv(index=False)
st.download_button("Download Shortlist CSV", csv, "scouting_shortlist.csv", "text/csv")
