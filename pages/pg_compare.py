
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os

st.title("\u2696\ufe0f Player Comparison")

gk_path = "scraped_data/engine_gk_profiles.csv"
if not os.path.exists(gk_path):
    st.error("Run `python integrate_gk_engine.py` first.")
    st.stop()

gk = pd.read_csv(gk_path)
for col in gk.columns:
    if col not in ["gk_player_id", "gk_name", "gk_team", "league", "best_zone"]:
        gk[col] = pd.to_numeric(gk[col], errors="coerce")

gk_names = sorted(gk["gk_name"].dropna().unique().tolist())

col1, col2 = st.columns(2)
gk1_name = col1.selectbox("Goalkeeper A", gk_names, index=0)
gk2_name = col2.selectbox("Goalkeeper B", gk_names, index=min(1, len(gk_names)-1))

if gk1_name and gk2_name:
    gk1 = gk[gk["gk_name"] == gk1_name].iloc[0]
    gk2 = gk[gk["gk_name"] == gk2_name].iloc[0]

    # ── Metric Cards ─────────────────────────────────────────────────
    st.markdown("### Key Metrics")
    metrics = [
        ("Save %", "save_pct"),
        ("Goals Prev/M", "goals_prevented_pm"),
        ("Clean Sheet %", "clean_sheet_pct"),
        ("Adversity Idx", "adversity_index"),
        ("H/A Delta", "ha_save_delta"),
        ("Consistency CV", "consistency_cv"),
    ]
    cols = st.columns(len(metrics))
    for i, (label, key) in enumerate(metrics):
        v1 = gk1.get(key, 0) or 0
        v2 = gk2.get(key, 0) or 0
        cols[i].metric(
            label,
            f"{v1:.2f}" if isinstance(v1, float) else str(v1),
            delta=f"{v1 - v2:+.2f} vs B" if isinstance(v1, float) else None,
        )

    # ── Overlaid Radar ───────────────────────────────────────────────
    st.markdown("### Radar Comparison")
    radar_keys = {
        "Save %":          "save_pct",
        "Goals Prev/M x100": "goals_prevented_pm",
        "Clean Sheet %":   "clean_sheet_pct",
        "Home Save %":     "home_save_pct",
        "Away Save %":     "away_save_pct",
        "vs Hard Save %":  "vs_hard_save_pct",
        "Loss Resilience": "loss_resilience",
    }

    categories = list(radar_keys.keys())

    def get_vals(row):
        vals = []
        for label, key in radar_keys.items():
            v = row.get(key, 0) or 0
            if "Prev/M" in label:
                v = max(v * 100, 0)
            vals.append(round(v, 1))
        return vals

    vals1 = get_vals(gk1)
    vals2 = get_vals(gk2)

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=vals1 + [vals1[0]], theta=categories + [categories[0]],
        fill="toself", name=f"{gk1_name} ({gk1['gk_team']})",
        line=dict(color="#1f77b4"),
    ))
    fig.add_trace(go.Scatterpolar(
        r=vals2 + [vals2[0]], theta=categories + [categories[0]],
        fill="toself", name=f"{gk2_name} ({gk2['gk_team']})",
        line=dict(color="#ff7f0e"),
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        height=500,
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Context Split Table ──────────────────────────────────────────
    st.markdown("### Context Splits")
    splits = pd.DataFrame({
        "Context": ["Baseline", "Home", "Away", "vs Hard Opponents", "vs Easy Opponents",
                     "Wins", "Draws", "Losses"],
        f"{gk1_name} Save %": [
            gk1.get("save_pct"), gk1.get("home_save_pct"), gk1.get("away_save_pct"),
            gk1.get("vs_hard_save_pct"), gk1.get("vs_easy_save_pct"),
            gk1.get("win_save_pct"), gk1.get("draw_save_pct"), gk1.get("loss_save_pct"),
        ],
        f"{gk2_name} Save %": [
            gk2.get("save_pct"), gk2.get("home_save_pct"), gk2.get("away_save_pct"),
            gk2.get("vs_hard_save_pct"), gk2.get("vs_easy_save_pct"),
            gk2.get("win_save_pct"), gk2.get("draw_save_pct"), gk2.get("loss_save_pct"),
        ],
    })
    st.dataframe(splits, use_container_width=True, hide_index=True)

    # ── Zone Breakdown ───────────────────────────────────────────────
    st.markdown("### Zone Goals Prevented")
    zone_df = pd.DataFrame({
        "Zone": ["Six-Yard Box", "Penalty Area", "Outside Box"],
        gk1_name: [gk1.get("zone_gp_six_yard", 0), gk1.get("zone_gp_pen_area", 0),
                    gk1.get("zone_gp_outside_box", 0)],
        gk2_name: [gk2.get("zone_gp_six_yard", 0), gk2.get("zone_gp_pen_area", 0),
                    gk2.get("zone_gp_outside_box", 0)],
    })
    st.dataframe(zone_df, use_container_width=True, hide_index=True)

    # ── Info ─────────────────────────────────────────────────────────
    st.markdown("---")
    c1, c2 = st.columns(2)
    c1.markdown(f"**{gk1_name}**: {gk1['gk_team']} ({gk1['league']}), {int(gk1.get('matches', 0))} matches, Best zone: {gk1.get('best_zone', 'N/A')}")
    c2.markdown(f"**{gk2_name}**: {gk2['gk_team']} ({gk2['league']}), {int(gk2.get('matches', 0))} matches, Best zone: {gk2.get('best_zone', 'N/A')}")
