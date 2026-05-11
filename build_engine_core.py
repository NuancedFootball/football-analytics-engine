import os, sys, math
import numpy as np
import pandas as pd
from collections import defaultdict
from scipy.spatial.distance import cosine
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

D = "scraped_data"
GRID_X = 16
GRID_Y = 12
N_ITER = 5
MIN_MINUTES = 450


def coord_to_cell(x, y):
    return min(int(float(x) * GRID_X), GRID_X - 1), min(int(float(y) * GRID_Y), GRID_Y - 1)


def compute_xt_grid(shot_subset, label=""):
    shoot_ct = np.zeros((GRID_X, GRID_Y))
    move_ct = np.zeros((GRID_X, GRID_Y))
    goal_ct = np.zeros((GRID_X, GRID_Y))
    T = np.zeros((GRID_X, GRID_Y, GRID_X, GRID_Y))

    for _, s in shot_subset.iterrows():
        try:
            x, y = float(s["X"]), float(s["Y"])
        except (ValueError, TypeError, KeyError):
            continue
        cx, cy = coord_to_cell(x, y)
        result = str(s.get("result", ""))
        is_goal = result == "Goal"

        shoot_ct[cx, cy] += 1
        if is_goal:
            goal_ct[cx, cy] += 1

        assisted = s.get("player_assisted")
        if pd.notna(assisted) and str(assisted).strip():
            ax = max(0.0, x - 0.08 + np.random.normal(0, 0.02))
            ay = np.clip(y + np.random.choice([-0.08, 0.08]) + np.random.normal(0, 0.03), 0, 1)
            acx, acy = coord_to_cell(ax, ay)
            move_ct[acx, acy] += 1
            T[acx, acy, cx, cy] += 1

    total = shoot_ct + move_ct
    total[total == 0] = 1
    s_prob = shoot_ct / total
    m_prob = move_ct / total
    g_prob = np.zeros((GRID_X, GRID_Y))
    mask = shoot_ct > 0
    g_prob[mask] = goal_ct[mask] / shoot_ct[mask]

    for i in range(GRID_X):
        for j in range(GRID_Y):
            ts = T[i, j].sum()
            if ts > 0:
                T[i, j] /= ts

    xT = np.zeros((GRID_X, GRID_Y))
    for _ in range(N_ITER):
        nxt = np.zeros((GRID_X, GRID_Y))
        for i in range(GRID_X):
            for j in range(GRID_Y):
                nxt[i, j] = s_prob[i, j] * g_prob[i, j] + m_prob[i, j] * np.sum(T[i, j] * xT)
        xT = nxt

    if label:
        print("    [{}] max={:.4f} mean={:.6f} shots={}".format(label, xT.max(), xT.mean(), int(shoot_ct.sum())))
    return xT


def build_xt():
    print("")
    print("=" * 60)
    print("PHASE 1: Expected Threat (xT) Surface")
    print("=" * 60)

    shots = pd.read_csv(os.path.join(D, "gk_shots_raw.csv"))
    mi = pd.read_csv(os.path.join(D, "gk_match_index.csv"))
    ml = mi.set_index("match_id")["league"].to_dict()
    if "league" not in shots.columns:
        shots["league"] = shots["match_id"].map(ml)

    shots["shooting_team"] = shots.apply(
        lambda r: r.get("h_team", "") if r.get("h_a") == "h" else r.get("a_team", ""), axis=1)

    print("  Shots loaded: {}".format(len(shots)))

    print("  Computing global xT...")
    global_xt = compute_xt_grid(shots, "GLOBAL")

    league_xts = {}
    for lg in sorted(shots["league"].dropna().unique()):
        lg_shots = shots[shots["league"] == lg]
        if len(lg_shots) >= 200:
            league_xts[lg] = compute_xt_grid(lg_shots, lg)

    team_xts = {}
    for tm in sorted(shots["shooting_team"].dropna().unique()):
        tm_shots = shots[shots["shooting_team"] == tm]
        if len(tm_shots) >= 80:
            team_xts[tm] = compute_xt_grid(tm_shots, "")
    print("  Team xT surfaces: {}".format(len(team_xts)))

    rows = []
    for lg, xt in league_xts.items():
        for i in range(GRID_X):
            for j in range(GRID_Y):
                rows.append({"entity": lg, "entity_type": "league", "cell_x": i, "cell_y": j, "xT": round(xt[i, j], 6)})
    for i in range(GRID_X):
        for j in range(GRID_Y):
            rows.append({"entity": "GLOBAL", "entity_type": "global", "cell_x": i, "cell_y": j, "xT": round(global_xt[i, j], 6)})
    pd.DataFrame(rows).to_csv(os.path.join(D, "engine_xt_league.csv"), index=False)

    rows = []
    for tm, xt in team_xts.items():
        for i in range(GRID_X):
            for j in range(GRID_Y):
                rows.append({"entity": tm, "entity_type": "team", "cell_x": i, "cell_y": j, "xT": round(xt[i, j], 6)})
    pd.DataFrame(rows).to_csv(os.path.join(D, "engine_xt_team.csv"), index=False)

    np.savez(os.path.join(D, "engine_xt_master.npz"), global_xt=global_xt)
    print("  Saved engine_xt_league.csv, engine_xt_team.csv, engine_xt_master.npz")
    return global_xt, team_xts


def build_cpa(global_xt=None, team_xts=None):
    print("")
    print("=" * 60)
    print("PHASE 2: Contextual Performance Adjustment (CPA)")
    print("=" * 60)

    rosters = pd.read_csv(os.path.join(D, "gk_rosters_raw.csv"))
    shots = pd.read_csv(os.path.join(D, "gk_shots_raw.csv"))
    mi = pd.read_csv(os.path.join(D, "gk_match_index.csv"))
    ml = mi.set_index("match_id")["league"].to_dict()

    if "league" not in shots.columns:
        shots["league"] = shots["match_id"].map(ml)

    # League Difficulty Index
    print("  Computing League Difficulty Index...")
    league_stats = {}
    for lg in mi["league"].unique():
        lgm = mi[mi["league"] == lg]
        lgs = shots[shots["league"] == lg]
        nm = len(lgm)
        if nm == 0:
            continue
        tg = 0
        txg = 0.0
        for _, m in lgm.iterrows():
            try:
                tg += int(m.get("h_goals", 0)) + int(m.get("a_goals", 0))
            except (ValueError, TypeError):
                pass
            try:
                txg += float(m.get("h_xG", 0)) + float(m.get("a_xG", 0))
            except (ValueError, TypeError):
                pass
        gpm = tg / max(nm, 1)
        spm = len(lgs) / max(nm, 1)
        league_stats[lg] = {"goals_pm": gpm, "shots_pm": spm, "xg_pm": txg / max(nm, 1)}

    ldf = pd.DataFrame(league_stats).T
    ldf["score_diff"] = 1.0 / ldf["goals_pm"]
    ldf["def_quality"] = ldf["shots_pm"] / ldf["goals_pm"]
    for c in ["score_diff", "def_quality"]:
        std = ldf[c].std()
        ldf[c + "_z"] = (ldf[c] - ldf[c].mean()) / (std if std > 0 else 1)
    ldf["LDI_raw"] = (ldf["score_diff_z"] + ldf["def_quality_z"]) / 2
    mn, mx = ldf["LDI_raw"].min(), ldf["LDI_raw"].max()
    if mx > mn:
        ldf["LDI"] = 0.85 + 0.30 * (ldf["LDI_raw"] - mn) / (mx - mn)
    else:
        ldf["LDI"] = 1.0
    ldi = ldf["LDI"].to_dict()
    for lg, v in sorted(ldi.items(), key=lambda x: -x[1]):
        print("    {:20s}: LDI = {:.3f}  ({:.2f} goals/match)".format(lg, v, league_stats[lg]["goals_pm"]))

    # Opponent Quality
    print("  Computing Opponent Quality Adjustments...")
    team_def = defaultdict(list)
    mt_info = {}
    for _, m in mi.iterrows():
        mid = m["match_id"]
        try:
            hxg = float(m.get("h_xG", 0))
            axg = float(m.get("a_xG", 0))
        except (ValueError, TypeError):
            continue
        ht = m.get("h_team", "")
        at = m.get("a_team", "")
        mt_info[mid] = {"h_team": ht, "a_team": at, "h_goals": m.get("h_goals", 0), "a_goals": m.get("a_goals", 0)}
        if ht:
            team_def[ht].append(axg)
        if at:
            team_def[at].append(hxg)

    team_xga = {t: np.mean(v) for t, v in team_def.items() if v}
    xga_vals = list(team_xga.values())
    if xga_vals:
        q25 = np.percentile(xga_vals, 25)
        q75 = np.percentile(xga_vals, 75)
    else:
        q25, q75 = 1.0, 1.5
    oqa = {}
    for t, xga in team_xga.items():
        if xga <= q25:
            oqa[t] = 1.15
        elif xga >= q75:
            oqa[t] = 0.85
        else:
            oqa[t] = 1.15 - 0.30 * (xga - q25) / max(q75 - q25, 0.01)

    top5 = sorted(oqa.items(), key=lambda x: -x[1])[:5]
    bot5 = sorted(oqa.items(), key=lambda x: x[1])[:5]
    print("    Top 5 toughest opponents:")
    for t, v in top5:
        print("      {:25s}: OQA={:.3f} xGA={:.2f}".format(t, v, team_xga[t]))
    print("    Top 5 weakest opponents:")
    for t, v in bot5:
        print("      {:25s}: OQA={:.3f} xGA={:.2f}".format(t, v, team_xga[t]))

    # Player profiles
    print("  Building player profiles...")
    xga_med = np.median(xga_vals) if xga_vals else 1.2
    pstats = {}

    for _, row in rosters.iterrows():
        pid = row.get("player_id")
        if pd.isna(pid):
            continue
        pid = str(int(float(pid)))
        mid = row.get("match_id")
        mins = float(row.get("time", 0))
        if mins <= 0:
            continue

        league = ml.get(mid, "")
        h_a = row.get("h_a", "")
        mt = mt_info.get(mid, {})
        if h_a == "h":
            opp = mt.get("a_team", "")
            own = mt.get("h_team", "")
            tg = int(mt.get("h_goals", 0))
            og = int(mt.get("a_goals", 0))
        else:
            opp = mt.get("h_team", "")
            own = mt.get("a_team", "")
            tg = int(mt.get("a_goals", 0))
            og = int(mt.get("h_goals", 0))

        result = "W" if tg > og else ("L" if tg < og else "D")
        lm = ldi.get(league, 1.0)
        om = oqa.get(opp, 1.0)

        if pid not in pstats:
            pstats[pid] = {
                "player_id": pid, "player": row.get("player", ""), "team": own,
                "league": league, "position": row.get("position", ""),
                "matches": 0, "total_minutes": 0,
                "goals": 0, "xG": 0, "assists": 0, "xA": 0,
                "shots": 0, "key_passes": 0, "xGChain": 0, "xGBuildup": 0,
                "cpa_goals": 0, "cpa_xG": 0, "cpa_xA": 0, "cpa_xGChain": 0, "cpa_xGBuildup": 0,
                "min_home": 0, "min_away": 0, "xG_home": 0, "xG_away": 0,
                "xG_win": 0, "xG_loss": 0, "xG_draw": 0,
                "min_win": 0, "min_loss": 0, "min_draw": 0,
                "matches_vs_top": 0, "xG_vs_top": 0, "min_vs_top": 0,
                "matches_vs_bot": 0, "xG_vs_bot": 0, "min_vs_bot": 0,
            }

        ps = pstats[pid]
        ps["matches"] += 1
        ps["total_minutes"] += mins

        for s in ["goals", "shots", "key_passes", "assists"]:
            try:
                ps[s] += float(row.get(s, 0))
            except (ValueError, TypeError):
                pass
        for s in ["xG", "xA", "xGChain", "xGBuildup"]:
            try:
                v = float(row.get(s, 0))
                ps[s] += v
                ps["cpa_" + s] += v * lm * om
            except (ValueError, TypeError):
                pass
        try:
            ps["cpa_goals"] += float(row.get("goals", 0)) * lm * om
        except (ValueError, TypeError):
            pass

        xgv = 0
        try:
            xgv = float(row.get("xG", 0))
        except (ValueError, TypeError):
            pass

        if h_a == "h":
            ps["min_home"] += mins
            ps["xG_home"] += xgv
        else:
            ps["min_away"] += mins
            ps["xG_away"] += xgv

        if result == "W":
            ps["xG_win"] += xgv
            ps["min_win"] += mins
        elif result == "L":
            ps["xG_loss"] += xgv
            ps["min_loss"] += mins
        else:
            ps["xG_draw"] += xgv
            ps["min_draw"] += mins

        opp_xga = team_xga.get(opp, xga_med)
        if opp_xga < xga_med:
            ps["matches_vs_top"] += 1
            ps["xG_vs_top"] += xgv
            ps["min_vs_top"] += mins
        else:
            ps["matches_vs_bot"] += 1
            ps["xG_vs_bot"] += xgv
            ps["min_vs_bot"] += mins

    # Per-90 and derived
    profiles = []
    for pid, ps in pstats.items():
        mins = ps["total_minutes"]
        if mins < MIN_MINUTES:
            continue
        p90 = 90.0 / mins
        pr = dict(ps)
        for s in ["goals", "xG", "xA", "shots", "key_passes", "xGChain", "xGBuildup"]:
            pr[s + "_p90"] = ps[s] * p90
        for s in ["goals", "xG", "xA", "xGChain", "xGBuildup"]:
            pr["cpa_" + s + "_p90"] = ps["cpa_" + s] * p90
        pr["xGI_p90"] = (ps["xG"] + ps["xA"]) * p90
        pr["cpa_xGI_p90"] = (ps["cpa_xG"] + ps["cpa_xA"]) * p90
        pr["goal_involvement_p90"] = (ps["goals"] + ps["assists"]) * p90
        pr["xG_overperf"] = ps["goals"] - ps["xG"]
        pr["xG_overperf_p90"] = (ps["goals"] - ps["xG"]) * p90

        pr["home_xG_p90"] = ps["xG_home"] * 90 / ps["min_home"] if ps["min_home"] > 90 else None
        pr["away_xG_p90"] = ps["xG_away"] * 90 / ps["min_away"] if ps["min_away"] > 90 else None
        pr["loss_xG_p90"] = ps["xG_loss"] * 90 / ps["min_loss"] if ps["min_loss"] > 90 else None
        pr["win_xG_p90"] = ps["xG_win"] * 90 / ps["min_win"] if ps["min_win"] > 90 else None
        pr["vs_top_xG_p90"] = ps["xG_vs_top"] * 90 / ps["min_vs_top"] if ps["min_vs_top"] > 90 else None
        pr["vs_bot_xG_p90"] = ps["xG_vs_bot"] * 90 / ps["min_vs_bot"] if ps["min_vs_bot"] > 90 else None
        pr["home_away_delta"] = (pr["home_xG_p90"] or 0) - (pr["away_xG_p90"] or 0)
        pr["resilience_ratio"] = (pr["loss_xG_p90"] or 0) / max(pr["xG_p90"], 0.001)
        pr["big_game_ratio"] = (pr["vs_top_xG_p90"] or 0) / max(pr["xG_p90"], 0.001)
        pr["LDI"] = ldi.get(ps["league"], 1.0)
        profiles.append(pr)

    # Role Burden
    team_chain = defaultdict(float)
    for p in profiles:
        team_chain[p["team"]] += p["xGChain_p90"]
    for p in profiles:
        p["role_burden"] = p["xGChain_p90"] / max(team_chain[p["team"]], 0.001)

    # Shot zone profile
    print("  Computing per-player shot zone profiles...")
    for p in profiles:
        pid = p["player_id"]
        ps = shots[shots["player_id"].astype(str) == pid]
        total_s = len(ps)
        if total_s == 0:
            p["pct_6yd"] = 0
            p["pct_pen"] = 0
            p["pct_outside"] = 0
            p["avg_shot_xG"] = 0
            p["avg_shot_dist"] = 0
            continue
        xvals = ps["X"].astype(float)
        in6 = (xvals > 0.94).sum()
        inpen = ((xvals > 0.83) & (xvals <= 0.94)).sum()
        outside = (xvals <= 0.83).sum()
        p["pct_6yd"] = round(in6 / total_s, 3)
        p["pct_pen"] = round(inpen / total_s, 3)
        p["pct_outside"] = round(outside / total_s, 3)
        try:
            p["avg_shot_xG"] = round(ps["xG"].astype(float).mean(), 4)
        except Exception:
            p["avg_shot_xG"] = 0
        try:
            yvals = ps["Y"].astype(float)
            p["avg_shot_dist"] = round(np.sqrt((1.0 - xvals) ** 2 + (0.5 - yvals) ** 2).mean(), 4)
        except Exception:
            p["avg_shot_dist"] = 0

    pdf = pd.DataFrame(profiles)
    pdf.to_csv(os.path.join(D, "engine_cpa_profiles.csv"), index=False)
    print("  Saved engine_cpa_profiles.csv ({} players)".format(len(pdf)))

    print("")
    print("  Top 10 CPA-adjusted xGI/90:")
    top = pdf.nlargest(10, "cpa_xGI_p90")
    for _, r in top.iterrows():
        print("    {:25s} ({:20s}) cpa_xGI={:.3f} RBI={:.3f}".format(
            r["player"], r["team"], r["cpa_xGI_p90"], r["role_burden"]))

    return pdf


def build_archetypes(pdf):
    print("")
    print("=" * 60)
    print("PHASE 3: Player Archetype Classification")
    print("=" * 60)

    feat_cols = [
        "xG_p90", "xA_p90", "shots_p90", "key_passes_p90",
        "xGChain_p90", "xGBuildup_p90", "goal_involvement_p90",
        "pct_6yd", "pct_pen", "pct_outside",
        "avg_shot_xG", "avg_shot_dist", "role_burden",
        "xG_overperf_p90", "resilience_ratio", "big_game_ratio",
    ]
    available = [c for c in feat_cols if c in pdf.columns]
    print("  Feature columns: {}".format(len(available)))

    X = pdf[available].fillna(0).values
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)

    n_comp = min(10, len(available), len(Xs))
    pca = PCA(n_components=n_comp)
    Xp = pca.fit_transform(Xs)
    explained = pca.explained_variance_ratio_.cumsum()
    print("  PCA: {} components, {:.1f}% variance explained".format(n_comp, explained[-1] * 100))

    best_k = 6
    best_sil = -1
    for k in range(5, 15):
        if k >= len(Xp):
            break
        km = KMeans(n_clusters=k, n_init=10, random_state=42)
        labels = km.fit_predict(Xp)
        sil = silhouette_score(Xp, labels)
        if sil > best_sil:
            best_sil = sil
            best_k = k
    print("  Optimal K={} (silhouette={:.3f})".format(best_k, best_sil))

    km = KMeans(n_clusters=best_k, n_init=20, random_state=42)
    pdf["cluster"] = km.fit_predict(Xp)

    centroids = pd.DataFrame(
        scaler.inverse_transform(pca.inverse_transform(km.cluster_centers_)),
        columns=available
    )

    base_names = [
        "Clinical Finisher", "Creative Conductor", "Deep Playmaker",
        "Engine Room", "Long-Range Threat", "Overperformer",
        "Goal Contributor", "Pressure Player", "Progressive Carrier",
        "Box-to-Box", "Wide Threat", "False Nine", "Target Man", "Shadow Striker",
    ]
    archetype_names = {}
    used = set()

    for ci in range(best_k):
        c = centroids.iloc[ci]
        name = None
        q = lambda col, pct: centroids[col].quantile(pct) if col in centroids.columns else 0

        if c.get("xG_p90", 0) > q("xG_p90", 0.75) and c.get("pct_6yd", 0) > q("pct_6yd", 0.6):
            name = "Clinical Finisher"
        elif c.get("xA_p90", 0) > q("xA_p90", 0.75) and c.get("key_passes_p90", 0) > q("key_passes_p90", 0.7):
            name = "Creative Conductor"
        elif c.get("xGBuildup_p90", 0) > q("xGBuildup_p90", 0.75) and c.get("xG_p90", 0) < q("xG_p90", 0.3):
            name = "Deep Playmaker"
        elif c.get("xGChain_p90", 0) > q("xGChain_p90", 0.7) and c.get("role_burden", 0) > q("role_burden", 0.7):
            name = "Engine Room"
        elif c.get("pct_outside", 0) > q("pct_outside", 0.7):
            name = "Long-Range Threat"
        elif c.get("xG_overperf_p90", 0) > q("xG_overperf_p90", 0.75):
            name = "Overperformer"
        elif c.get("goal_involvement_p90", 0) > q("goal_involvement_p90", 0.6):
            name = "Goal Contributor"
        elif c.get("resilience_ratio", 0) > q("resilience_ratio", 0.75):
            name = "Pressure Player"

        if name is None or name in used:
            for bn in base_names:
                if bn not in used:
                    name = bn
                    break
            else:
                name = "Profile {}".format(ci + 1)

        used.add(name)
        archetype_names[ci] = name

    pdf["archetype"] = pdf["cluster"].map(archetype_names)

    for i in range(min(3, n_comp)):
        pdf["pca_{}".format(i + 1)] = Xp[:, i]

    pdf.to_csv(os.path.join(D, "engine_cpa_profiles.csv"), index=False)
    print("")
    print("  Archetype distribution:")
    for name, count in pdf["archetype"].value_counts().items():
        print("    {:25s}: {} players".format(name, count))

    centroids["archetype"] = [archetype_names[i] for i in range(best_k)]
    centroids.to_csv(os.path.join(D, "engine_archetype_centroids.csv"), index=False)
    print("  Saved engine_archetype_centroids.csv")

    return pdf


def build_similarity(pdf):
    print("")
    print("=" * 60)
    print("PHASE 4: Similarity Engine")
    print("=" * 60)

    feat_cols = [
        "cpa_xG_p90", "cpa_xA_p90", "shots_p90", "key_passes_p90",
        "cpa_xGChain_p90", "cpa_xGBuildup_p90",
        "pct_6yd", "pct_pen", "pct_outside",
        "avg_shot_xG", "role_burden",
        "resilience_ratio", "big_game_ratio", "home_away_delta",
    ]
    available = [c for c in feat_cols if c in pdf.columns]
    print("  Similarity features: {}".format(len(available)))

    X = pdf[available].fillna(0).values
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)

    results = []
    n = len(pdf)
    for i in range(n):
        vec_i = Xs[i]
        sims = []
        for j in range(n):
            if i == j:
                continue
            try:
                d = 1.0 - cosine(vec_i, Xs[j])
            except Exception:
                d = 0
            sims.append((j, d))
        sims.sort(key=lambda x: -x[1])

        r = {
            "player": pdf.iloc[i]["player"],
            "team": pdf.iloc[i]["team"],
            "league": pdf.iloc[i]["league"],
            "archetype": pdf.iloc[i].get("archetype", ""),
            "player_id": pdf.iloc[i]["player_id"],
        }
        for k in range(min(20, len(sims))):
            idx = sims[k][0]
            r["sim_{}_name".format(k + 1)] = pdf.iloc[idx]["player"]
            r["sim_{}_team".format(k + 1)] = pdf.iloc[idx]["team"]
            r["sim_{}_league".format(k + 1)] = pdf.iloc[idx]["league"]
            r["sim_{}_archetype".format(k + 1)] = pdf.iloc[idx].get("archetype", "")
            r["sim_{}_score".format(k + 1)] = round(sims[k][1], 4)
        results.append(r)
        if (i + 1) % 200 == 0:
            print("  {}/{} done...".format(i + 1, n))

    sd = pd.DataFrame(results)
    sd.to_csv(os.path.join(D, "engine_similarity.csv"), index=False)
    print("  Saved engine_similarity.csv ({} players)".format(len(sd)))

    for _, r in sd.head(5).iterrows():
        print("")
        print("  {} ({}, {}):".format(r["player"], r["team"], r.get("archetype", "")))
        for k in range(1, 6):
            nm = r.get("sim_{}_name".format(k), "")
            tm = r.get("sim_{}_team".format(k), "")
            sc = r.get("sim_{}_score".format(k), 0)
            if nm:
                print("    {}. {} ({}) -- {:.4f}".format(k, nm, tm, sc))


def build_ecosystems(pdf):
    print("")
    print("=" * 60)
    print("PHASE 5: Team Ecosystem Profiles v3")
    print("=" * 60)

    mi = pd.read_csv(os.path.join(D, "gk_match_index.csv"))

    xt_team = None
    xt_path = os.path.join(D, "engine_xt_team.csv")
    if os.path.exists(xt_path):
        xt_team = pd.read_csv(xt_path)

    teams = pdf.groupby("team")
    eco_rows = []

    for team_name, grp in teams:
        league = grp["league"].mode().iloc[0] if len(grp["league"].mode()) > 0 else ""
        n_players = len(grp)

        total_xg = grp["xG_p90"].sum()
        total_xa = grp["xA_p90"].sum()
        total_chain = grp["xGChain_p90"].sum()
        total_buildup = grp["xGBuildup_p90"].sum()

        xa_shares = (grp["xA_p90"] / max(total_xa, 0.001)) ** 2
        creativity_conc = xa_shares.sum()
        xg_shares = (grp["xG_p90"] / max(total_xg, 0.001)) ** 2
        goal_conc = xg_shares.sum()
        bu_shares = (grp["xGBuildup_p90"] / max(total_buildup, 0.001)) ** 2
        buildup_conc = bu_shares.sum()

        avg_res = grp["resilience_ratio"].mean()
        avg_bg = grp["big_game_ratio"].mean()
        n_arch = grp["archetype"].nunique() if "archetype" in grp.columns else 0

        avg_6yd = grp["pct_6yd"].mean()
        avg_pen = grp["pct_pen"].mean()
        avg_out = grp["pct_outside"].mean()

        threat_zones = ""
        if xt_team is not None:
            tm_xt = xt_team[xt_team["entity"] == team_name]
            if len(tm_xt) > 0:
                top3 = tm_xt.nlargest(3, "xT")
                parts = []
                for _, rr in top3.iterrows():
                    parts.append("({},{})={:.4f}".format(int(rr["cell_x"]), int(rr["cell_y"]), rr["xT"]))
                threat_zones = "; ".join(parts)

        team_matches = mi[(mi["h_team"] == team_name) | (mi["a_team"] == team_name)]
        wins = draws = losses = 0
        total_gf = total_ga = 0
        total_xgf = total_xga_val = 0.0
        for _, m in team_matches.iterrows():
            try:
                hg = int(m["h_goals"])
                ag = int(m["a_goals"])
                hxg = float(m["h_xG"])
                axg = float(m["a_xG"])
            except (ValueError, TypeError):
                continue
            if m["h_team"] == team_name:
                total_gf += hg
                total_ga += ag
                total_xgf += hxg
                total_xga_val += axg
                if hg > ag:
                    wins += 1
                elif hg < ag:
                    losses += 1
                else:
                    draws += 1
            else:
                total_gf += ag
                total_ga += hg
                total_xgf += axg
                total_xga_val += hxg
                if ag > hg:
                    wins += 1
                elif ag < hg:
                    losses += 1
                else:
                    draws += 1

        nm = len(team_matches)
        ppg = (wins * 3 + draws) / max(nm, 1)

        eco_rows.append({
            "team": team_name, "league": league, "players": n_players,
            "matches": nm, "wins": wins, "draws": draws, "losses": losses,
            "ppg": round(ppg, 2),
            "goals_for": total_gf, "goals_against": total_ga,
            "xGF": round(total_xgf, 2), "xGA": round(total_xga_val, 2),
            "xGD": round(total_xgf - total_xga_val, 2),
            "creativity_concentration": round(creativity_conc, 4),
            "goal_concentration": round(goal_conc, 4),
            "buildup_concentration": round(buildup_conc, 4),
            "avg_resilience": round(avg_res, 3),
            "avg_big_game": round(avg_bg, 3),
            "n_archetypes": n_arch,
            "avg_pct_6yd": round(avg_6yd, 3),
            "avg_pct_pen": round(avg_pen, 3),
            "avg_pct_outside": round(avg_out, 3),
            "threat_corridors": threat_zones,
        })

    edf = pd.DataFrame(eco_rows)
    edf.to_csv(os.path.join(D, "engine_team_ecosystems_v3.csv"), index=False)
    print("  Saved engine_team_ecosystems_v3.csv ({} teams)".format(len(edf)))

    print("")
    print("  Top 10 by xGD:")
    for _, r in edf.nlargest(10, "xGD").iterrows():
        print("    {:25s} ({:12s}) xGD={:+.2f} ppg={:.2f} goal_conc={:.3f}".format(
            r["team"], r["league"], r["xGD"], r["ppg"], r["goal_concentration"]))

    return edf


def build_adversity(pdf):
    print("")
    print("=" * 60)
    print("PHASE 6: Adversity and Resilience Profiles")
    print("=" * 60)

    cols = ["player_id", "player", "team", "league", "archetype",
            "matches", "total_minutes", "xG_p90", "cpa_xGI_p90",
            "resilience_ratio", "big_game_ratio", "home_away_delta",
            "xG_overperf_p90", "role_burden"]
    available = [c for c in cols if c in pdf.columns]
    adv = pdf[available].copy()

    for c in ["resilience_ratio", "big_game_ratio"]:
        if c in adv.columns:
            std = adv[c].std()
            adv[c + "_z"] = (adv[c] - adv[c].mean()) / (std if std > 0 else 1)

    score_cols = [c for c in adv.columns if c.endswith("_z")]
    if score_cols:
        adv["adversity_score"] = adv[score_cols].mean(axis=1)
        adv["adversity_rank"] = adv["adversity_score"].rank(ascending=False).astype(int)
    else:
        adv["adversity_score"] = 0
        adv["adversity_rank"] = 0

    adv.to_csv(os.path.join(D, "engine_adversity.csv"), index=False)
    print("  Saved engine_adversity.csv ({} players)".format(len(adv)))

    print("")
    print("  Top 15 Pressure Players (highest adversity score):")
    for _, r in adv.nlargest(15, "adversity_score").iterrows():
        print("    {:25s} ({:20s}) adv={:.3f} res={:.3f} big={:.3f}".format(
            r["player"], r["team"], r["adversity_score"],
            r.get("resilience_ratio", 0), r.get("big_game_ratio", 0)))

    return adv


def build_transfer_intel(pdf):
    print("")
    print("=" * 60)
    print("PHASE 7: Transfer Intelligence")
    print("=" * 60)

    ti_cols = ["player_id", "player", "team", "league", "archetype",
               "matches", "total_minutes", "position",
               "cpa_xGI_p90", "cpa_xG_p90", "cpa_xA_p90",
               "xG_p90", "xA_p90", "role_burden",
               "resilience_ratio", "big_game_ratio",
               "xG_overperf_p90", "LDI"]
    available = [c for c in ti_cols if c in pdf.columns]
    ti = pdf[available].copy()

    ti["output_efficiency"] = ti["cpa_xGI_p90"] / ti["role_burden"].clip(lower=0.01)
    ti["growth_signal"] = ti["xG_overperf_p90"].clip(lower=-0.5, upper=0.5)

    for c in ["cpa_xGI_p90", "output_efficiency", "resilience_ratio", "big_game_ratio", "growth_signal"]:
        if c in ti.columns:
            std = ti[c].std()
            ti[c + "_z"] = (ti[c] - ti[c].mean()) / (std if std > 0 else 1)

    z_cols = [c for c in ti.columns if c.endswith("_z")]
    if z_cols:
        ti["transfer_score"] = ti[z_cols].mean(axis=1)
        ti["transfer_rank"] = ti["transfer_score"].rank(ascending=False).astype(int)

    ti.to_csv(os.path.join(D, "engine_transfer_intel.csv"), index=False)
    print("  Saved engine_transfer_intel.csv ({} players)".format(len(ti)))

    print("")
    print("  Top 20 Transfer Targets (composite score):")
    for _, r in ti.nlargest(20, "transfer_score").iterrows():
        print("    {:25s} ({:20s}, {:10s}) T-score={:.3f} cpa_xGI={:.3f} eff={:.2f}".format(
            r["player"], r["team"], r["league"],
            r["transfer_score"], r["cpa_xGI_p90"], r["output_efficiency"]))

    return ti


if __name__ == "__main__":
    print("=" * 60)
    print("NUANCED PLAYER <> LEAGUE <> TEAM ENGINE v2.0")
    print("Big 5 Leagues -- 2025/26 Season")
    print("=" * 60)

    global_xt, team_xts = build_xt()
    pdf = build_cpa(global_xt, team_xts)
    pdf = build_archetypes(pdf)
    build_similarity(pdf)
    edf = build_ecosystems(pdf)
    build_adversity(pdf)
    build_transfer_intel(pdf)

    print("")
    print("=" * 60)
    print("ENGINE v2.0 COMPLETE")
    print("=" * 60)
    print("")
    print("Output files in {}/:".format(D))
    for f in sorted(os.listdir(D)):
        if f.startswith("engine_"):
            sz = os.path.getsize(os.path.join(D, f))
            print("  {:45s} {:.0f} KB".format(f, sz / 1024))
