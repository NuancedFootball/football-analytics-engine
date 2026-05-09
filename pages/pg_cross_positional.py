
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.figure_factory as ff
import os

st.title("\U0001f504 Cross-Positional Dependencies")

corr_path = "scraped_data/engine_positional_correlations.csv"
dep_path  = "scraped_data/engine_team_dependencies.csv"

if not os.path.exists(corr_path):
    st.error("Run `python cross_positional_analysis.py` first.")
    st.stop()

# ── Correlation Heatmap ──────────────────────────────────────────────
st.markdown("### GK Metrics vs Positional Output (League-Wide Correlations)")
corr = pd.read_csv(corr_path, index_col=0)

# Select subset for readability
gk_rows = [r for r in corr.index if r in ["goals_conceded", "saves", "save_pct", "xGA", "clean_sheet"]]
pos_cols_display = [c for c in corr.columns if any(c.endswith(f"_{p}") for p in ["DEF", "MID", "ATT_MID", "FWD"])]

# Limit to key stats
key_stats = ["total_xGBuildup", "total_xGChain", "total_xG", "total_xA"]
pos_cols_filtered = [c for c in pos_cols_display if any(c.startswith(s) for s in key_stats)]

if gk_rows and pos_cols_filtered:
    subset = corr.loc[gk_rows, pos_cols_filtered]

    # Clean column names for display
    rename_map = {}
    for c in pos_cols_filtered:
        parts = c.split("_")
        stat = "_".join(parts[1:-1])
        pos = parts[-1]
        rename_map[c] = f"{pos}: {stat}"

    subset_display = subset.rename(columns=rename_map)

    fig = px.imshow(
        subset_display.values,
        x=subset_display.columns.tolist(),
        y=subset_display.index.tolist(),
        color_continuous_scale="RdBu_r",
        zmin=-0.5, zmax=0.5,
        text_auto=".2f",
        aspect="auto",
    )
    fig.update_layout(height=400, xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("""
    **Reading the heatmap:** Positive (red) correlations mean that when the positional group
    produces more, the GK metric also increases. For example, a positive correlation between
    `clean_sheet` and `DEF: xGBuildup` suggests that when defenders contribute more to buildup,
    the team is more likely to keep a clean sheet.
    """)

# ── Team-Level Dependencies ─────────────────────────────────────────
if os.path.exists(dep_path):
    st.markdown("### Team-Level: GK-Attack Dependency")
    dep = pd.read_csv(dep_path)
    for col in dep.columns:
        if col not in ["team", "league"]:
            dep[col] = pd.to_numeric(dep[col], errors="coerce")

    leagues = ["All"] + sorted(dep["league"].dropna().unique().tolist())
    sel = st.selectbox("Filter League", leagues, key="xpos_league")
    dep_f = dep if sel == "All" else dep[dep["league"] == sel]

    if "corr_save_pct_vs_team_xG" in dep_f.columns:
        st.markdown("#### Teams Where GK Performance Most Impacts Attack")
        fig2 = px.bar(
            dep_f.dropna(subset=["corr_save_pct_vs_team_xG"]).sort_values(
                "corr_save_pct_vs_team_xG", ascending=True).tail(20),
            x="corr_save_pct_vs_team_xG", y="team", orientation="h",
            color="league",
            labels={"corr_save_pct_vs_team_xG": "Correlation: GK Save% vs Team xG",
                    "team": ""},
        )
        fig2.update_layout(height=600)
        st.plotly_chart(fig2, use_container_width=True)

    if "corr_gp_vs_DEF_buildup" in dep_f.columns:
        st.markdown("#### GK Goals Prevented vs Defensive Buildup Correlation")
        fig3 = px.bar(
            dep_f.dropna(subset=["corr_gp_vs_DEF_buildup"]).sort_values(
                "corr_gp_vs_DEF_buildup", ascending=True).tail(20),
            x="corr_gp_vs_DEF_buildup", y="team", orientation="h",
            color="league",
            labels={"corr_gp_vs_DEF_buildup": "Correlation: GK Goals Prev. vs DEF xGBuildup",
                    "team": ""},
        )
        fig3.update_layout(height=600)
        st.plotly_chart(fig3, use_container_width=True)
