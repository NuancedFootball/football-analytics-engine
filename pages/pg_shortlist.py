import streamlit as st
import pandas as pd
import plotly.express as px

st.title("Scouting Shortlist Builder")
D = "scraped_data"

@st.cache_data
def load_profiles():
    return pd.read_csv("{}/engine_cpa_profiles.csv".format(D))

@st.cache_data
def load_transfer():
    try:
        return pd.read_csv("{}/engine_transfer_intel.csv".format(D))
    except Exception:
        return pd.DataFrame()

prof = load_profiles()
ti = load_transfer()

st.markdown("Build a scouting shortlist by defining target criteria.")

col1, col2 = st.columns(2)
with col1:
    tgt_league = st.multiselect("Target Leagues", sorted(prof["league"].dropna().unique()))
    arch_options = sorted(prof["archetype"].dropna().unique()) if "archetype" in prof.columns else []
    tgt_archetype = st.multiselect("Archetype", arch_options)
    min_matches = st.slider("Min Matches", 5, 30, 10)

with col2:
    min_xgi = st.slider("Min CPA xGI/90", 0.0, 1.5, 0.1, 0.05)
    min_resilience = st.slider("Min Resilience Ratio", 0.0, 3.0, 0.0, 0.1)
    min_big_game = st.slider("Min Big-Game Ratio", 0.0, 3.0, 0.0, 0.1)

fdf = prof.copy()
if tgt_league:
    fdf = fdf[fdf["league"].isin(tgt_league)]
if tgt_archetype and "archetype" in fdf.columns:
    fdf = fdf[fdf["archetype"].isin(tgt_archetype)]
fdf = fdf[fdf["matches"] >= min_matches]
fdf = fdf[fdf["cpa_xGI_p90"] >= min_xgi]
if "resilience_ratio" in fdf.columns:
    fdf = fdf[fdf["resilience_ratio"] >= min_resilience]
if "big_game_ratio" in fdf.columns:
    fdf = fdf[fdf["big_game_ratio"] >= min_big_game]

if len(ti) > 0 and "transfer_score" in ti.columns:
    fdf = fdf.merge(ti[["player_id","transfer_score","transfer_rank","output_efficiency"]],
                     on="player_id", how="left", suffixes=("","_ti"))

st.subheader("{} candidates".format(len(fdf)))
sort_options = ["cpa_xGI_p90","transfer_score","resilience_ratio","big_game_ratio","role_burden"]
avail_sort = [s for s in sort_options if s in fdf.columns]
sort_by = st.selectbox("Sort by", avail_sort)

show_cols = ["player","team","league","archetype","matches","total_minutes",
             "cpa_xGI_p90","cpa_xG_p90","cpa_xA_p90","role_burden",
             "resilience_ratio","big_game_ratio","xG_overperf_p90",
             "transfer_score","output_efficiency"]
avail_show = [c for c in show_cols if c in fdf.columns]

st.dataframe(fdf[avail_show].sort_values(sort_by, ascending=False).head(50),
             use_container_width=True, hide_index=True)

if st.button("Export Shortlist to CSV"):
    export = fdf[avail_show].sort_values(sort_by, ascending=False)
    csv_data = export.to_csv(index=False)
    st.download_button("Download CSV", csv_data, "scouting_shortlist.csv", "text/csv")

if len(fdf) > 1:
    y_col = "resilience_ratio" if "resilience_ratio" in fdf.columns else "role_burden"
    color_col = "archetype" if "archetype" in fdf.columns else "league"
    fig = px.scatter(fdf, x="cpa_xGI_p90", y=y_col, hover_name="player",
                     color=color_col, size="matches", size_max=15, opacity=0.7,
                     title="Shortlist: Output vs Resilience")
    fig.update_layout(height=500)
    st.plotly_chart(fig, use_container_width=True)
