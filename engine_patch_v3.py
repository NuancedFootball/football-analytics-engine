#!/usr/bin/env python3
"""
Engine Patch v3.0 — Credibility Overhaul
1. Position group classification
2. Minutes reliability tiers
3. Age brackets
4. Position-weighted scoring
5. Financial feasibility metrics
6. OQA fix in build_engine_core.py
"""
import pandas as pd
import numpy as np
import pathlib

SD = pathlib.Path("scraped_data")

print("=" * 60)
print("ENGINE PATCH v3.0 — Credibility Overhaul")
print("=" * 60)

cpa = pd.read_csv(SD / "engine_cpa_profiles.csv")
adv = pd.read_csv(SD / "engine_adversity.csv")
ti  = pd.read_csv(SD / "engine_transfer_intel.csv")
eco = pd.read_csv(SD / "engine_team_ecosystems_v3.csv")

print("Loaded CPA=" + str(len(cpa)) + " ADV=" + str(len(adv)) + " TI=" + str(len(ti)))

# ─────────────────────────────────────────────────────────────
# 1. POSITION GROUP CLASSIFICATION
# ─────────────────────────────────────────────────────────────
print("\n" + "-" * 60)
print("1. Position Group Classification")
print("-" * 60)

# Map Understat position codes to groups
POS_MAP = {
    "GK": "Goalkeeper",
    "DC": "Centre-Back", "Sub": "Rotation",
    "DL": "Full-Back", "DR": "Full-Back",
    "DML": "Full-Back", "DMR": "Full-Back",
    "DMC": "Defensive Mid", "MC": "Central Mid",
    "ML": "Wide Mid", "MR": "Wide Mid",
    "AMC": "Attacking Mid", "AML": "Winger", "AMR": "Winger",
    "FW": "Striker", "FWL": "Striker", "FWR": "Striker",
}

cpa["position_group"] = cpa["position"].map(POS_MAP).fillna("Other")

# Also create a broader band for scoring purposes
BAND_MAP = {
    "Goalkeeper": "Goalkeeper",
    "Centre-Back": "Defender",
    "Full-Back": "Defender",
    "Defensive Mid": "Midfielder",
    "Central Mid": "Midfielder",
    "Wide Mid": "Midfielder",
    "Attacking Mid": "Attacker",
    "Winger": "Attacker",
    "Striker": "Attacker",
    "Rotation": "Rotation",
    "Other": "Other",
}
cpa["position_band"] = cpa["position_group"].map(BAND_MAP).fillna("Other")

print("  Position groups:")
for g, c in cpa["position_group"].value_counts().items():
    print("    " + str(g).ljust(20) + str(c))

# ─────────────────────────────────────────────────────────────
# 2. MINUTES RELIABILITY TIERS
# ─────────────────────────────────────────────────────────────
print("\n" + "-" * 60)
print("2. Minutes Reliability Tiers")
print("-" * 60)

def assign_reliability(mins):
    if mins >= 2700:
        return "Elite Sample"
    elif mins >= 1800:
        return "Strong Sample"
    elif mins >= 1350:
        return "Moderate Sample"
    elif mins >= 900:
        return "Limited Sample"
    else:
        return "Small Sample"

cpa["reliability_tier"] = cpa["total_minutes"].apply(assign_reliability)

print("  Reliability tiers:")
for t, c in cpa["reliability_tier"].value_counts().items():
    print("    " + str(t).ljust(20) + str(c))

# ─────────────────────────────────────────────────────────────
# 3. AGE BRACKETS
# ─────────────────────────────────────────────────────────────
print("\n" + "-" * 60)
print("3. Age Brackets")
print("-" * 60)

def assign_age_bracket(age):
    if pd.isna(age):
        return "Unknown"
    age = float(age)
    if age < 21:
        return "Prospect (U21)"
    elif age < 24:
        return "Emerging (21-23)"
    elif age < 28:
        return "Prime (24-27)"
    elif age < 32:
        return "Peak (28-31)"
    else:
        return "Veteran (32+)"

cpa["age_bracket"] = cpa["age"].apply(assign_age_bracket) if "age" in cpa.columns else "Unknown"

if "age" in cpa.columns:
    print("  Age brackets:")
    for b, c in cpa["age_bracket"].value_counts().items():
        print("    " + str(b).ljust(22) + str(c))

# ─────────────────────────────────────────────────────────────
# 4. POSITION-WEIGHTED COMPOSITE SCORE
# ─────────────────────────────────────────────────────────────
print("\n" + "-" * 60)
print("4. Position-Weighted Composite Score")
print("-" * 60)

# Different positions should be evaluated differently:
# Attackers: weight xG, xA, finishing heavily
# Midfielders: weight xA, xGChain, xGBuildup, vision
# Defenders: weight xGBuildup, defensive awareness, resilience
# GK: separate track entirely

def compute_position_score(row):
    band = row.get("position_band", "Other")
    mins = row.get("total_minutes", 0)

    # Minutes reliability multiplier (0.6 to 1.0)
    if mins >= 2700:
        mins_mult = 1.0
    elif mins >= 1800:
        mins_mult = 0.95
    elif mins >= 1350:
        mins_mult = 0.85
    elif mins >= 900:
        mins_mult = 0.75
    else:
        mins_mult = 0.60

    cpa_xgi = row.get("cpa_xGI_p90", 0) or 0
    cpa_xg = row.get("cpa_xG_p90", 0) or 0
    cpa_xa = row.get("cpa_xA_p90", 0) or 0
    chain = row.get("cpa_xGChain_p90", 0) or 0
    buildup = row.get("cpa_xGBuildup_p90", 0) or 0
    burden = row.get("role_burden", 0) or 0
    resil = row.get("resilience_ratio", 0) or 0
    big_g = row.get("big_game_ratio", 0) or 0

    if band == "Attacker":
        raw = (cpa_xg * 0.35 + cpa_xa * 0.20 + chain * 0.15 +
               burden * 2.0 * 0.10 + resil * 0.10 + big_g * 0.10)
    elif band == "Midfielder":
        raw = (cpa_xa * 0.25 + chain * 0.20 + buildup * 0.20 +
               cpa_xg * 0.10 + burden * 2.0 * 0.10 + resil * 0.15)
    elif band == "Defender":
        raw = (buildup * 0.30 + resil * 0.25 + big_g * 0.20 +
               chain * 0.15 + burden * 2.0 * 0.10)
    elif band == "Goalkeeper":
        raw = resil * 0.40 + big_g * 0.40 + burden * 2.0 * 0.20
    else:
        raw = cpa_xgi * 0.50 + resil * 0.25 + big_g * 0.25

    return round(raw * mins_mult, 4)

cpa["position_score"] = cpa.apply(compute_position_score, axis=1)

# Compute percentile rank within position group
cpa["position_pctile"] = cpa.groupby("position_group")["position_score"].rank(pct=True)
cpa["position_pctile"] = (cpa["position_pctile"] * 100).round(1)

print("  Top 5 by position_score per band:")
for band in ["Attacker", "Midfielder", "Defender"]:
    sub = cpa[cpa["position_band"] == band].nlargest(5, "position_score")
    print("  " + band + ":")
    for _, r in sub.iterrows():
        print("    " + str(r["player"]).ljust(25) + " (" + str(r["position_group"]).ljust(15) +
              ") score=" + str(r["position_score"]) + " pctile=" + str(r["position_pctile"]))

# ─────────────────────────────────────────────────────────────
# 5. FINANCIAL FEASIBILITY METRICS
# ─────────────────────────────────────────────────────────────
print("\n" + "-" * 60)
print("5. Financial Feasibility Metrics")
print("-" * 60)

# Team squad values
if "value_eur" in cpa.columns:
    team_value = cpa.groupby("team")["value_eur"].agg(
        squad_value="sum", avg_player_value="mean", squad_size="count"
    ).reset_index()

    # Merge team financial context into ecosystem
    eco = eco.merge(team_value, on="team", how="left")
    eco.to_csv(SD / "engine_team_ecosystems_v3.csv", index=False)
    print("  Team ecosystems updated with squad_value, avg_player_value")

    # Player affordability ratio: player_value / team_avg_value
    team_avg = dict(zip(team_value["team"], team_value["avg_player_value"]))
    cpa["value_vs_team_avg"] = cpa.apply(
        lambda r: round(r.get("value_eur", 0) / max(team_avg.get(r["team"], 1), 1), 2)
        if pd.notna(r.get("value_eur")) else None, axis=1
    )

    # Value-per-output: value_eur / cpa_xGI_p90 (lower = better value)
    cpa["value_per_xgi"] = cpa.apply(
        lambda r: round(r.get("value_eur", 0) / max(r.get("cpa_xGI_p90", 0.001), 0.001))
        if pd.notna(r.get("value_eur")) and r.get("cpa_xGI_p90", 0) > 0.01 else None,
        axis=1
    )

    # Discount score: high output + low value = bargain
    # Normalized: position_pctile / (value_percentile + 1)
    val_pctile = cpa["value_eur"].rank(pct=True).fillna(0.5)
    cpa["discount_score"] = ((cpa["position_pctile"].fillna(50) / 100) /
                              (val_pctile + 0.01)).round(3)

    has_val = cpa["value_eur"].notna().sum()
    print("  Players with value data: " + str(has_val))
    print("  Top 10 discount scores (best bargains):")
    bargains = cpa[cpa["position_band"].isin(["Attacker","Midfielder","Defender"])].nlargest(10, "discount_score")
    for _, r in bargains.iterrows():
        val_str = str(int(r.get("value_eur", 0) / 1e6)) + "M" if pd.notna(r.get("value_eur")) else "?"
        print("    " + str(r["player"]).ljust(25) + " " + str(r["position_group"]).ljust(15) +
              " val=" + val_str + " pctile=" + str(r["position_pctile"]) +
              " discount=" + str(r["discount_score"]))
else:
    print("  WARNING: No value_eur column found")

# ─────────────────────────────────────────────────────────────
# 6. OQA FIX in build_engine_core.py
# ─────────────────────────────────────────────────────────────
print("\n" + "-" * 60)
print("6. OQA Fix (Lines 206-218)")
print("-" * 60)

engine_path = pathlib.Path("build_engine_core.py")
if engine_path.exists():
    lines = engine_path.read_text(encoding="utf-8").split("\n")

    # Find and replace the OQA block (lines ~211-218)
    new_lines = []
    skip_until_top5 = False
    for i, line in enumerate(lines):
        # Replace the OQA computation block
        if "oqa = {}" in line and not skip_until_top5:
            # Insert new continuous OQA logic
            indent = "    "
            new_lines.append(indent + "oqa = {}")
            new_lines.append(indent + "# Continuous percentile-based OQA (0.80 to 1.20)")
            new_lines.append(indent + "xga_arr = np.array(list(team_xga.values()))")
            new_lines.append(indent + "xga_mean = xga_arr.mean()")
            new_lines.append(indent + "xga_std = max(xga_arr.std(), 0.01)")
            new_lines.append(indent + "for t, xga in team_xga.items():")
            new_lines.append(indent + "    z = (xga_mean - xga) / xga_std")
            new_lines.append(indent + "    oqa[t] = round(np.clip(1.0 + z * 0.10, 0.80, 1.20), 4)")
            skip_until_top5 = True
            continue

        if skip_until_top5:
            if "top5 = sorted" in line:
                skip_until_top5 = False
                new_lines.append(line)
            # Skip old OQA lines
            continue

        new_lines.append(line)

    engine_path.write_text("\n".join(new_lines), encoding="utf-8")
    print("  Replaced OQA block with continuous z-score scaling (0.80-1.20)")
    print("  Re-run build_engine_core.py for full effect")
else:
    print("  WARNING: build_engine_core.py not found")

# ─────────────────────────────────────────────────────────────
# Save updated CPA
# ─────────────────────────────────────────────────────────────
print("\n" + "-" * 60)
print("Saving updated files")
print("-" * 60)

new_cols = ["position_group", "position_band", "reliability_tier",
            "age_bracket", "position_score", "position_pctile",
            "value_vs_team_avg", "value_per_xgi", "discount_score"]
added = [c for c in new_cols if c in cpa.columns]
print("  New CPA columns: " + str(added))
cpa.to_csv(SD / "engine_cpa_profiles.csv", index=False)
print("  Saved engine_cpa_profiles.csv (" + str(len(cpa)) + " rows, " +
      str(len(cpa.columns)) + " cols)")

# Propagate position_group, age_bracket, reliability_tier to ADV and TI
propagate = ["position_group", "position_band", "reliability_tier",
             "age_bracket", "position_score", "position_pctile", "discount_score"]
prop_available = [c for c in propagate if c in cpa.columns]
prop_df = cpa[["player_id"] + prop_available].drop_duplicates(subset="player_id")

for name, df, path in [("adversity", adv, "engine_adversity.csv"),
                        ("transfer_intel", ti, "engine_transfer_intel.csv")]:
    drop_existing = [c for c in prop_available if c in df.columns]
    if drop_existing:
        df = df.drop(columns=drop_existing)
    df = df.merge(prop_df, on="player_id", how="left")
    df.to_csv(SD / path, index=False)
    print("  Saved " + path + " (" + str(len(df.columns)) + " cols)")

print("\n" + "=" * 60)
print("PATCH v3.0 COMPLETE")
print("=" * 60)
print()
print("New data dimensions added:")
print("  - position_group: 10 groups (Centre-Back, Full-Back, Striker, etc.)")
print("  - position_band: 5 bands (Attacker, Midfielder, Defender, GK, Rotation)")
print("  - reliability_tier: 5 tiers based on minutes played")
print("  - age_bracket: 5 brackets (Prospect through Veteran)")
print("  - position_score: Position-weighted composite (different weights per band)")
print("  - position_pctile: Percentile rank within position group")
print("  - discount_score: Performance-per-value ratio (higher = better bargain)")
print("  - value_per_xgi: Cost per unit of CPA output")
print("  - value_vs_team_avg: Player value relative to their team average")
print()
print("OQA fix applied to build_engine_core.py (re-run for full effect)")
