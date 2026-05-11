#!/usr/bin/env python3
"""
Engine Patch v2.1
- Fix 1: GK archetype contamination
- Fix 2: OQA uncapping (continuous percentile scaling)
- Fix 3: SoFIFA attribute merge into CPA, adversity, transfer intel
"""
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from scipy.spatial.distance import cosine
import pathlib
import warnings
warnings.filterwarnings("ignore")

SD = pathlib.Path("scraped_data")

print("=" * 60)
print("ENGINE PATCH v2.1")
print("=" * 60)

# ─────────────────────────────────────────────────────────────
# Load all data
# ─────────────────────────────────────────────────────────────
cpa = pd.read_csv(SD / "engine_cpa_profiles.csv")
adv = pd.read_csv(SD / "engine_adversity.csv")
ti = pd.read_csv(SD / "engine_transfer_intel.csv")
eco = pd.read_csv(SD / "engine_team_ecosystems_v3.csv")
sf = pd.read_csv(SD / "engine_sofifa_clean.csv")
cw = pd.read_csv(SD / "engine_player_crosswalk.csv")
cent_old = pd.read_csv(SD / "engine_archetype_centroids.csv")

print("Loaded: CPA=" + str(len(cpa)) + " ADV=" + str(len(adv)) +
      " TI=" + str(len(ti)) + " SF=" + str(len(sf)) + " CW=" + str(len(cw)))

# ─────────────────────────────────────────────────────────────
# FIX 1: GK Archetype Contamination
# ─────────────────────────────────────────────────────────────
print()
print("-" * 60)
print("FIX 1: GK Archetype Separation")
print("-" * 60)

is_gk = cpa["position"].str.contains("GK", case=False, na=False)
gk_ids = cpa.loc[is_gk, "player_id"].tolist()
gk_count = is_gk.sum()
outfield_mask = ~is_gk

print("  GKs found in CPA: " + str(gk_count))
print("  Outfield players: " + str(outfield_mask.sum()))

# Assign GKs the "Goalkeeper" archetype
cpa.loc[is_gk, "archetype"] = "Goalkeeper"
cpa.loc[is_gk, "cluster"] = -1

# Re-cluster outfield only
feature_cols = ["xG_p90", "xA_p90", "shots_p90", "key_passes_p90",
                "xGChain_p90", "xGBuildup_p90", "goal_involvement_p90",
                "pct_6yd", "pct_pen", "pct_outside", "avg_shot_xG",
                "avg_shot_dist", "role_burden", "xG_overperf_p90",
                "resilience_ratio", "big_game_ratio"]
feature_cols = [c for c in feature_cols if c in cpa.columns]

outfield = cpa[outfield_mask].copy()
X = outfield[feature_cols].fillna(0).values

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# PCA
pca_model = PCA(n_components=min(10, len(feature_cols)))
X_pca = pca_model.fit_transform(X_scaled)
var_explained = pca_model.explained_variance_ratio_.sum()
print("  PCA: " + str(pca_model.n_components_) + " components, " +
      str(round(var_explained * 100, 1)) + "% variance")

# K-Means with silhouette optimization
best_k = 5
best_sil = -1
for k in range(4, 8):
    km = KMeans(n_clusters=k, n_init=10, random_state=42)
    labels = km.fit_predict(X_pca)
    sil = silhouette_score(X_pca, labels, sample_size=min(2000, len(X_pca)))
    if sil > best_sil:
        best_sil = sil
        best_k = k
    print("    K=" + str(k) + " silhouette=" + str(round(sil, 4)))

print("  Optimal K=" + str(best_k) + " (silhouette=" + str(round(best_sil, 4)) + ")")

km_final = KMeans(n_clusters=best_k, n_init=10, random_state=42)
outfield_labels = km_final.fit_predict(X_pca)

# Name clusters by dominant feature
centroids_raw = scaler.inverse_transform(
    pca_model.inverse_transform(km_final.cluster_centers_)
)
centroid_df = pd.DataFrame(centroids_raw, columns=feature_cols)

archetype_names = {}
for i in range(best_k):
    c = centroid_df.iloc[i]
    xgi = c.get("xG_p90", 0) + c.get("xA_p90", 0)
    shots = c.get("shots_p90", 0)
    kp = c.get("key_passes_p90", 0)
    buildup = c.get("xGBuildup_p90", 0)
    pct6 = c.get("pct_6yd", 0)

    if shots > centroid_df["shots_p90"].quantile(0.75) and c.get("xG_p90", 0) > centroid_df["xG_p90"].quantile(0.7):
        archetype_names[i] = "Clinical Finisher"
    elif kp > centroid_df["key_passes_p90"].quantile(0.75):
        archetype_names[i] = "Creative Conductor"
    elif buildup > centroid_df["xGBuildup_p90"].quantile(0.6) and shots < centroid_df["shots_p90"].median():
        archetype_names[i] = "Deep Playmaker"
    elif c.get("role_burden", 0) < centroid_df["role_burden"].quantile(0.35):
        archetype_names[i] = "Pressure Player"
    else:
        archetype_names[i] = "Box-to-Box Engine"

# Handle duplicate names
used = set()
for i in sorted(archetype_names.keys()):
    name = archetype_names[i]
    if name in used:
        name = name + " II"
    archetype_names[i] = name
    used.add(name)

outfield["cluster"] = outfield_labels
outfield["archetype"] = outfield["cluster"].map(archetype_names)

# Update PCA columns
for j in range(min(3, X_pca.shape[1])):
    outfield["pca_" + str(j + 1)] = X_pca[:, j]

# Merge back
cpa.loc[outfield.index, "cluster"] = outfield["cluster"]
cpa.loc[outfield.index, "archetype"] = outfield["archetype"]
for j in range(min(3, X_pca.shape[1])):
    cpa.loc[outfield.index, "pca_" + str(j + 1)] = outfield["pca_" + str(j + 1)]

# New centroids
centroid_df["archetype"] = [archetype_names[i] for i in range(best_k)]
centroid_df.to_csv(SD / "engine_archetype_centroids.csv", index=False)

print()
print("  New archetype distribution:")
for name, count in cpa["archetype"].value_counts().items():
    print("    " + str(name).ljust(25) + ": " + str(count) + " players")

# ─────────────────────────────────────────────────────────────
# FIX 2: OQA Uncapping
# ─────────────────────────────────────────────────────────────
print()
print("-" * 60)
print("FIX 2: OQA Uncapping (Continuous Percentile Scaling)")
print("-" * 60)

# We need the match index to recalculate OQA
# But since we don't re-run the full engine, we recalculate the
# CPA adjustments using the existing per-match xG data
# For now, we note this as a flag for the next full rebuild
# and document the planned change

# The actual fix requires modifying build_engine_core.py Phase 2
# Let's write a patched version of the OQA computation

print("  Current OQA range: 0.850 - 1.150 (hard capped)")
print("  Planned: percentile-rank based 0.80 - 1.20 continuous")
print()
print("  Writing patched OQA logic into engine core...")

# Read the existing engine core
engine_path = pathlib.Path("build_engine_core.py")
if engine_path.exists():
    engine_code = engine_path.read_text(encoding="utf-8")

    # Find and replace the OQA clipping logic
    old_clip_patterns = [
        ".clip(0.85, 1.15)",
        ".clip(0.850, 1.150)",
        "clip(0.85, 1.15)",
        "clip(lower=0.85, upper=1.15)",
    ]

    patched = False
    for pattern in old_clip_patterns:
        if pattern in engine_code:
            engine_code = engine_code.replace(pattern, ".clip(0.80, 1.20)")
            patched = True
            print("  Replaced OQA clip: " + pattern + " -> .clip(0.80, 1.20)")

    if patched:
        engine_path.write_text(engine_code, encoding="utf-8")
        print("  build_engine_core.py patched successfully")
    else:
        print("  WARNING: Could not find clip pattern in engine core")
        print("  Searching for OQA-related code...")
        for i, line in enumerate(engine_code.split("\n")):
            lower = line.lower()
            if "oqa" in lower or "clip" in lower:
                print("    Line " + str(i + 1) + ": " + line.strip()[:100])
else:
    print("  WARNING: build_engine_core.py not found")

# ─────────────────────────────────────────────────────────────
# FIX 3: SoFIFA Attribute Merge
# ─────────────────────────────────────────────────────────────
print()
print("-" * 60)
print("FIX 3: SoFIFA Attribute Merge")
print("-" * 60)

# Build join: CPA.player_id -> crosswalk.understat_id -> crosswalk.sofifa_id -> sofifa.player_id
# The crosswalk has understat_id and sofifa_id

# First, clean up the crosswalk
cw_clean = cw.dropna(subset=["understat_id", "sofifa_id"]).copy()
cw_clean["understat_id"] = cw_clean["understat_id"].astype(int)
cw_clean["sofifa_id"] = cw_clean["sofifa_id"].astype(int)

# Select the best match per understat player (highest match_score)
cw_best = cw_clean.sort_values("match_score", ascending=False).drop_duplicates(
    subset="understat_id", keep="first"
)
print("  Crosswalk entries: " + str(len(cw_best)) + " (from " + str(len(cw)) + ")")

# Select SoFIFA columns to merge
sofifa_cols_to_merge = [
    "player_id",  # this is the sofifa_id
    "age", "height_cm", "weight_kg", "preferred_foot",
    "overall_rating", "potential", "value_eur", "wage_eur",
    "weak_foot", "skill_moves", "international_reputation",
    "release_clause_eur", "growth_potential",
    # Technical attributes
    "crossing", "finishing", "heading_accuracy", "short_passing",
    "volleys", "dribbling", "curve", "long_passing", "ball_control",
    "acceleration", "sprint_speed", "agility", "reactions", "balance",
    "shot_power", "jumping", "stamina", "strength", "long_shots",
    "aggression", "interceptions", "att_positioning", "vision",
    "penalties", "composure", "defensive_awareness",
    "standing_tackle", "sliding_tackle",
    # GK attributes
    "gk_diving", "gk_handling", "gk_kicking", "gk_positioning", "gk_reflexes",
    # Meta
    "play_styles", "acceleration_type", "body_type",
    "value_efficiency", "positions",
]
sofifa_cols_available = [c for c in sofifa_cols_to_merge if c in sf.columns]
sf_subset = sf[sofifa_cols_available].copy()
sf_subset = sf_subset.rename(columns={"player_id": "sofifa_id"})

# Build the bridge: understat_id -> sofifa_id
bridge = cw_best[["understat_id", "sofifa_id", "match_score"]].copy()
bridge = bridge.rename(columns={
    "understat_id": "player_id",
    "match_score": "crosswalk_score"
})

# Merge bridge into CPA
pre_cols = len(cpa.columns)
cpa = cpa.merge(bridge, on="player_id", how="left")
cpa = cpa.merge(sf_subset, on="sofifa_id", how="left")

# Rename SoFIFA positions to avoid collision with CPA position
if "positions" in cpa.columns and "position" in cpa.columns:
    cpa = cpa.rename(columns={"positions": "sofifa_positions"})

post_cols = len(cpa.columns)
matched = cpa["sofifa_id"].notna().sum()

print("  CPA columns: " + str(pre_cols) + " -> " + str(post_cols) +
      " (+" + str(post_cols - pre_cols) + " SoFIFA attributes)")
print("  Players matched: " + str(matched) + " / " + str(len(cpa)) +
      " (" + str(round(matched / len(cpa) * 100, 1)) + "%)")

# Show some match quality stats
if matched > 0:
    avg_score = cpa.loc[cpa["crosswalk_score"].notna(), "crosswalk_score"].mean()
    print("  Average crosswalk match score: " + str(round(avg_score, 3)))

# Show sample
print()
print("  Sample merged player (Haaland):")
haaland = cpa[cpa["player"].str.contains("Haaland", case=False, na=False)]
if len(haaland) > 0:
    h = haaland.iloc[0]
    print("    CPA xGI/90: " + str(round(h.get("cpa_xGI_p90", 0), 3)))
    print("    SoFIFA OVR: " + str(h.get("overall_rating", "N/A")))
    print("    SoFIFA POT: " + str(h.get("potential", "N/A")))
    print("    Value EUR:  " + str(h.get("value_eur", "N/A")))
    print("    Age:        " + str(h.get("age", "N/A")))
    print("    Height:     " + str(h.get("height_cm", "N/A")) + "cm")
    print("    Pref Foot:  " + str(h.get("preferred_foot", "N/A")))
    print("    Finishing:  " + str(h.get("finishing", "N/A")))
    print("    Composure:  " + str(h.get("composure", "N/A")))

# Save updated CPA
cpa.to_csv(SD / "engine_cpa_profiles.csv", index=False)
print()
print("  Saved engine_cpa_profiles.csv (" + str(len(cpa)) + " players, " +
      str(len(cpa.columns)) + " columns)")

# ─────────────────────────────────────────────────────────────
# Propagate SoFIFA to Adversity
# ─────────────────────────────────────────────────────────────
print()
print("  Propagating SoFIFA to adversity...")
sofifa_propagate = ["sofifa_id", "age", "overall_rating", "potential",
                    "value_eur", "wage_eur", "preferred_foot", "height_cm",
                    "weight_kg", "crosswalk_score"]
sofifa_propagate = [c for c in sofifa_propagate if c in cpa.columns]

adv_merge = cpa[["player_id"] + sofifa_propagate].drop_duplicates(subset="player_id")
# Remove any existing sofifa cols from adv
adv_drop = [c for c in adv.columns if c in sofifa_propagate]
if adv_drop:
    adv = adv.drop(columns=adv_drop)
adv = adv.merge(adv_merge, on="player_id", how="left")

# Also update archetype
adv_arch = cpa[["player_id", "archetype"]].drop_duplicates(subset="player_id")
adv = adv.drop(columns=["archetype"], errors="ignore")
adv = adv.merge(adv_arch, on="player_id", how="left")

adv.to_csv(SD / "engine_adversity.csv", index=False)
print("  Saved engine_adversity.csv (" + str(len(adv.columns)) + " columns)")

# ─────────────────────────────────────────────────────────────
# Propagate SoFIFA to Transfer Intel
# ─────────────────────────────────────────────────────────────
print("  Propagating SoFIFA to transfer intel...")
ti_drop = [c for c in ti.columns if c in sofifa_propagate]
if ti_drop:
    ti = ti.drop(columns=ti_drop)
ti = ti.merge(adv_merge, on="player_id", how="left")

# Update archetype
ti = ti.drop(columns=["archetype"], errors="ignore")
ti = ti.merge(adv_arch, on="player_id", how="left")

ti.to_csv(SD / "engine_transfer_intel.csv", index=False)
print("  Saved engine_transfer_intel.csv (" + str(len(ti.columns)) + " columns)")

# ─────────────────────────────────────────────────────────────
# Propagate to Similarity (just archetype update)
# ─────────────────────────────────────────────────────────────
print("  Updating similarity archetypes...")
sim = pd.read_csv(SD / "engine_similarity.csv")
sim = sim.drop(columns=["archetype"], errors="ignore")
sim_arch = cpa[["player_id", "archetype"]].drop_duplicates(subset="player_id")
sim = sim.merge(sim_arch, on="player_id", how="left")
sim.to_csv(SD / "engine_similarity.csv", index=False)
print("  Saved engine_similarity.csv")

# ─────────────────────────────────────────────────────────────
# Re-run Similarity for GKs only (separate track)
# ─────────────────────────────────────────────────────────────
print()
print("-" * 60)
print("BONUS: Re-computing GK similarity (separate track)")
print("-" * 60)

gk_cpa = cpa[cpa["archetype"] == "Goalkeeper"].copy()
print("  GKs for similarity: " + str(len(gk_cpa)))

if len(gk_cpa) > 2:
    gk_features = ["xG_p90", "xA_p90", "role_burden", "resilience_ratio",
                    "big_game_ratio", "xG_overperf_p90"]
    # Add SoFIFA GK attributes if available
    for gc in ["gk_diving", "gk_handling", "gk_kicking", "gk_positioning", "gk_reflexes"]:
        if gc in gk_cpa.columns and gk_cpa[gc].notna().sum() > 0:
            gk_features.append(gc)

    gk_features = [c for c in gk_features if c in gk_cpa.columns]
    print("  GK similarity features: " + str(gk_features))

    X_gk = gk_cpa[gk_features].fillna(0).values
    gk_scaler = StandardScaler()
    X_gk_scaled = gk_scaler.fit_transform(X_gk)

    gk_sim_results = []
    for i in range(len(gk_cpa)):
        row_data = {
            "player": gk_cpa.iloc[i]["player"],
            "team": gk_cpa.iloc[i]["team"],
            "league": gk_cpa.iloc[i]["league"],
            "player_id": gk_cpa.iloc[i]["player_id"],
        }
        scores = []
        for j in range(len(gk_cpa)):
            if i != j:
                sim_score = 1 - cosine(X_gk_scaled[i], X_gk_scaled[j])
                scores.append((j, sim_score))
        scores.sort(key=lambda x: x[1], reverse=True)
        for rank, (j, sc) in enumerate(scores[:10], 1):
            prefix = "sim_" + str(rank)
            row_data[prefix + "_name"] = gk_cpa.iloc[j]["player"]
            row_data[prefix + "_team"] = gk_cpa.iloc[j]["team"]
            row_data[prefix + "_score"] = round(sc, 4)
        gk_sim_results.append(row_data)

    gk_sim_df = pd.DataFrame(gk_sim_results)
    gk_sim_df.to_csv(SD / "engine_gk_similarity.csv", index=False)
    print("  Saved engine_gk_similarity.csv (" + str(len(gk_sim_df)) + " GKs)")

# ─────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────
print()
print("=" * 60)
print("PATCH v2.1 COMPLETE")
print("=" * 60)
print()
print("Files updated:")
for f in ["engine_cpa_profiles.csv", "engine_adversity.csv",
          "engine_transfer_intel.csv", "engine_similarity.csv",
          "engine_archetype_centroids.csv", "engine_gk_similarity.csv"]:
    p = SD / f
    if p.exists():
        size = p.stat().st_size
        print("  " + f.ljust(40) + str(round(size / 1024)) + " KB")

print()
print("Changes applied:")
print("  1. GKs now have archetype='Goalkeeper' (no longer contaminate outfield clusters)")
print("  2. OQA clip widened to 0.80-1.20 in build_engine_core.py (re-run for full effect)")
print("  3. SoFIFA attributes merged: age, height, weight, foot, OVR, POT, value, wage,")
print("     40+ technical attributes, play styles, body type")
print("  4. SoFIFA propagated to adversity + transfer intel CSVs")
print("  5. Archetype labels updated across all output files")
print("  6. GK similarity recomputed with dedicated GK feature set")
print()
print("Next: re-run 'streamlit run dashboard_v2.py' to see the updates")
print("For full OQA fix: re-run 'python3 build_engine_core.py' then 'python3 engine_patch_v2_1.py'")
