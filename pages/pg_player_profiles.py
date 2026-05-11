import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import pathlib
from glossary import show_glossary, show_methodology, player_card, sidebar_filters

st.title("Player Profiles (CPA-Adjusted)")
st.caption("Position-weighted scoring | SoFIFA attributes | Contextual normalization")

SD = pathlib.Path("scraped_data")

@st.cache_data
def load():
    return pd.read_csv(SD / "engine_cpa_profiles.csv") if (SD / "engine_cpa_profiles.csv").exists() else None

df = load()
if df is None:
    st.error("CPA profiles not found.")
    st.stop()

show_glossary()
fdf = sidebar_filters(df, prefix="pp")

st.subheader("Leaderboard (" + str(len(fdf)) + " players)")
sort_opts = ["position_score","position_pctile","cpa_xGI_p90","cpa_xG_p90","cpa_xA_p90","discount_score"]
sort_opts = [c for c in sort_opts if c in fdf.columns]
sort_col = st.selectbox("Sort by", sort_opts, key="pp_sort")

display_cols = ["player","team","league","position_group","archetype","age_bracket",
                "reliability_tier","position_score","position_pctile","cpa_xGI_p90",
                "overall_rating","value_eur","discount_score"]
display_cols = [c for c in display_cols if c in fdf.columns]
st.dataframe(fdf.nlargest(50, sort_col)[display_cols].reset_index(drop=True),
             use_container_width=True, height=600)

st.divider()
st.subheader("Player Card & Radar")
player_list = sorted(fdf["player"].unique().tolist())
if player_list:
    sel_p = st.selectbox("Select Player", player_list, key="pp_sel")
    row = fdf[fdf["player"] == sel_p].iloc[0]

    player_card(row)

    st.divider()

    # Position-appropriate radar
    band = row.get("position_band", "Other")
    if band == "Attacker":
        radar_cols = ["cpa_xG_p90","cpa_xA_p90","shots_p90","key_passes_p90","cpa_xGChain_p90","role_burden","resilience_ratio","big_game_ratio"]
    elif band == "Midfielder":
        radar_cols = ["cpa_xA_p90","cpa_xGChain_p90","cpa_xGBuildup_p90","cpa_xG_p90","key_passes_p90","role_burden","resilience_ratio"]
    elif band == "Defender":
        radar_cols = ["cpa_xGBuildup_p90","cpa_xGChain_p90","resilience_ratio","big_game_ratio","role_burden","key_passes_p90"]
    else:
        radar_cols = ["cpa_xGI_p90","resilience_ratio","big_game_ratio","role_burden"]

    radar_cols = [c for c in radar_cols if c in fdf.columns]

    if radar_cols:
        # Compare within position group
        pg = row.get("position_group", "All")
        comp = fdf[fdf["position_group"] == pg] if pg != "All" and "position_group" in fdf.columns else fdf
        vals = []
        for c in radar_cols:
            pctl = (comp[c] <= row[c]).mean()
            vals.append(round(pctl * 100, 1))

        labels = [c.replace("cpa_","").replace("_p90","").replace("_"," ").title() for c in radar_cols]

        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=vals + [vals[0]], theta=labels + [labels[0]],
            fill="toself", name=sel_p, line_color="#FF6B35"
        ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0,100])),
            showlegend=False,
            title=sel_p + " - Percentile Radar vs " + pg + " (" + str(len(comp)) + " players)",
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)

    # SoFIFA technical attributes
    tech_cols = ["finishing","dribbling","short_passing","vision","composure",
                 "sprint_speed","stamina","strength","defensive_awareness","standing_tackle"]
    tech_available = [c for c in tech_cols if c in row.index and str(row.get(c,"")) != "nan"]
    if tech_available:
        st.subheader("SoFIFA Technical Profile")
        tc1, tc2, tc3, tc4, tc5 = st.columns(5)
        for i, c in enumerate(tech_available[:10]):
            col = [tc1,tc2,tc3,tc4,tc5][i % 5]
            col.metric(c.replace("_"," ").title(), int(row[c]))

show_methodology()
