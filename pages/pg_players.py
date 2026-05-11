import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.title("Player Deep Dive")
D = "scraped_data"

@st.cache_data
def load():
    return pd.read_csv(f"{D}/engine_cpa_profiles.csv")

df = load()

col1, col2 = st.columns([1,2])
with col1:
    league = st.selectbox("League", ["All"] + sorted(df["league"].unique()))
    if league != "All":
        df = df[df["league"]==league]
    team = st.selectbox("Team", ["All"] + sorted(df["team"].unique()))
    if team != "All":
        df = df[df["team"]==team]
    archetype = st.selectbox("Archetype", ["All"] + sorted(df["archetype"].dropna().unique()))
    if archetype != "All":
        df = df[df["archetype"]==archetype]

player = st.selectbox("Select Player", df.sort_values("cpa_xGI_p90", ascending=False)["player"].unique())
p = df[df["player"]==player].iloc[0]

st.subheader(f"{p['player']} — {p['team']} ({p['league']})")

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Matches", int(p["matches"]))
m2.metric("Minutes", int(p["total_minutes"]))
m3.metric("CPA xGI/90", f"{p['cpa_xGI_p90']:.3f}")
m4.metric("Role Burden", f"{p['role_burden']:.3f}")
m5.metric("Archetype", p.get("archetype",""))

st.subheader("Radar Profile")
cats = ["xG_p90","xA_p90","shots_p90","key_passes_p90","xGChain_p90","xGBuildup_p90"]
labels = ["xG","xA","Shots","Key Pass","xGChain","xGBuildup"]
vals = [float(p.get(c,0)) for c in cats]

# Percentile within filtered data
pcts = []
for c in cats:
    col_vals = df[c].dropna()
    if len(col_vals) > 0:
        pcts.append(round((col_vals < p[c]).sum() / len(col_vals) * 100))
    else:
        pcts.append(50)

fig = go.Figure()
fig.add_trace(go.Scatterpolar(r=pcts, theta=labels, fill="toself", name="Percentile"))
fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0,100])),
                  height=400, margin=dict(t=30,b=30))
st.plotly_chart(fig, use_container_width=True)

st.subheader("Context Splits")
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("**Home vs Away**")
    h = p.get("home_xG_p90")
    a = p.get("away_xG_p90")
    if pd.notna(h) and pd.notna(a):
        st.metric("Home xG/90", f"{h:.3f}")
        st.metric("Away xG/90", f"{a:.3f}")
        st.metric("Delta", f"{float(h)-float(a):+.3f}")
with c2:
    st.markdown("**Game State**")
    w = p.get("win_xG_p90")
    l = p.get("loss_xG_p90")
    if pd.notna(w): st.metric("When Winning", f"{w:.3f}")
    if pd.notna(l): st.metric("When Trailing", f"{l:.3f}")
    st.metric("Resilience Ratio", f"{p.get('resilience_ratio',0):.3f}")
with c3:
    st.markdown("**Opponent Quality**")
    vt = p.get("vs_top_xG_p90")
    vb = p.get("vs_bot_xG_p90")
    if pd.notna(vt): st.metric("vs Top Defenses", f"{vt:.3f}")
    if pd.notna(vb): st.metric("vs Weak Defenses", f"{vb:.3f}")
    st.metric("Big Game Ratio", f"{p.get('big_game_ratio',0):.3f}")

st.subheader("Shot Zone Profile")
sz1, sz2, sz3 = st.columns(3)
sz1.metric("6-Yard Box", f"{p.get('pct_6yd',0)*100:.1f}%")
sz2.metric("Penalty Area", f"{p.get('pct_pen',0)*100:.1f}%")
sz3.metric("Outside Box", f"{p.get('pct_outside',0)*100:.1f}%")
