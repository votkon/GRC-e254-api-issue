#!/usr/bin/env python3
"""
Epoch 254 API Issue — Compensation Calculator

Eligibility criteria:
  - CPoC 1 confirmation ratio > 45.5%   (node was active before the bug window)
  - Final confirmation ratio  < 45.5%   (node was severely impacted by the end of epoch)
  - Actual rewards received = 0

Methodology:
  Baseline reward rate = total rewards of healthy participants / total weight of healthy participants
  Compensation per address = baseline_rate * weight  (actual rewards already 0)
"""

import json
import subprocess
import sys
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "gonka-segment-report", ".env"))

ARCHIVE_NODE = os.getenv("ARCHIVE_NODE_URL")
BINARY = os.getenv("INFERENCED_BINARY")

# Key block heights from analysis
EPOCH = 254
EPOCH_END_HEIGHT = 3936059
CPOC1_BEFORE  = 3928850  # last block before CPoC 1 concluded
CPOC1_HEIGHT  = 3928860  # CPoC 1 concluded

CPOC1_MIN_RATIO  = 0.455  # CPoC 1 ratio must be > 45.5%
FINAL_MAX_RATIO  = 0.455  # final confirmation ratio must be < 45.5%


def run_cli(args, height=None):
    cmd = [BINARY] + args + ["--node", ARCHIVE_NODE, "-o", "json"]
    if height:
        cmd += ["--height", str(height)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def get_epoch_members(height):
    d = run_cli(["query", "inference", "show-epoch-group-data", str(EPOCH)], height=height)
    if not d:
        return {}
    vw = d.get("epoch_group_data", d).get("validation_weights", [])
    return {
        x["member_address"]: {
            "weight": int(x.get("weight", 0)),
            "cw": int(x["confirmation_weight"]) if "confirmation_weight" in x else None,
        }
        for x in vw
    }


def get_rewards(address):
    d = run_cli([
        "query", "inference",
        "show-epoch-performance-summary-by-participant",
        str(EPOCH), address
    ])
    if not d:
        return 0
    return int(d.get("epochPerformanceSummary", {}).get("rewarded_coins", 0))


def conf_ratio(entry):
    if entry is None or entry.get("cw") is None:
        return None
    w = int(entry.get("weight", 0))
    cw = int(entry.get("cw", 0))
    return cw / w if w > 0 else 0.0


def main():
    print("Loading pre-computed participant data...", flush=True)
    data_file = os.path.join(os.path.dirname(__file__), "epoch254_participants.json")
    with open(data_file) as f:
        participants_map = {p["address"]: p for p in json.load(f)}

    print("Loading snapshots...", flush=True)
    after_cpoc1 = get_epoch_members(CPOC1_HEIGHT)     # state after CPoC 1
    after_epoch  = get_epoch_members(EPOCH_END_HEIGHT) # final state after all CPoCs

    healthy = []
    affected = []

    for addr, e1 in after_cpoc1.items():
        r1 = conf_ratio(e1)
        if r1 is None:
            continue

        e_final = after_epoch.get(addr)
        r_final = conf_ratio(e_final) if e_final is not None else 0.0
        if r_final is None:
            r_final = 0.0

        actual_rewards = participants_map.get(addr, {}).get("rewarded_ngonka", 0)
        weight = int(e1.get("weight", 0))

        if r1 > CPOC1_MIN_RATIO and r_final < FINAL_MAX_RATIO and actual_rewards == 0:
            affected.append({
                "address": addr,
                "weight": weight,
                "cpoc1_ratio": r1,
                "final_ratio": r_final,
                "actual_rewards_ngonka": actual_rewards,
            })
        elif r1 > CPOC1_MIN_RATIO and actual_rewards > 0 and r_final >= CPOC1_MIN_RATIO:
            healthy.append({
                "address": addr,
                "weight": weight,
                "conf_ratio": r_final,
                "rewards_ngonka": actual_rewards,
            })

    total_healthy_weight = sum(p["weight"] for p in healthy)
    total_healthy_rewards = sum(p["rewards_ngonka"] for p in healthy)
    baseline_rate = total_healthy_rewards / total_healthy_weight if total_healthy_weight > 0 else 0

    print(f"\nHealthy participants (CPoC1>45.5%, final>=45.5%, rewarded): {len(healthy)}")
    print(f"  Total weight  : {total_healthy_weight:,}")
    print(f"  Total rewards : {total_healthy_rewards / 1e9:,.2f} GONKA")
    print(f"  Baseline rate : {baseline_rate / 1e9 * 1000:.6f} GONKA per 1000 weight")

    print(f"\nAffected participants (CPoC1>45.5%, final<45.5%, rewards=0): {len(affected)}")

    results = []
    total_compensation = 0

    for p in affected:
        compensation = baseline_rate * p["weight"]
        total_compensation += compensation
        results.append({
            "address": p["address"],
            "weight": p["weight"],
            "cpoc1_ratio": p["cpoc1_ratio"],
            "final_ratio": p["final_ratio"],
            "compensation_ngonka": int(compensation),
            "compensation_gonka": compensation / 1e9,
        })

    results.sort(key=lambda x: x["compensation_ngonka"], reverse=True)

    print(f"\n{'='*80}")
    print("COMPENSATION SUMMARY — Epoch 254 API Issue")
    print(f"{'='*80}")
    print(f"{'Address':<50} {'Weight':>8} {'CPoC1':>7} {'Final':>7} {'Compensation (GONKA)':>20}")
    print(f"{'-'*80}")
    for r in results:
        print(
            f"{r['address']:<50} "
            f"{r['weight']:>8,} "
            f"{r['cpoc1_ratio']:>7.1%} "
            f"{r['final_ratio']:>7.1%} "
            f"{r['compensation_gonka']:>20.4f}"
        )
    print(f"{'-'*80}")
    print(f"  Total: {total_compensation / 1e9:,.4f} GONKA")

    csv_file = os.path.join(os.path.dirname(__file__), "compensation.csv")
    with open(csv_file, "w") as f:
        f.write("address,weight,cpoc1_ratio,final_ratio,compensation_ngonka,compensation_gonka\n")
        for r in results:
            f.write(
                f"{r['address']},{r['weight']},{r['cpoc1_ratio']:.4f},{r['final_ratio']:.4f},"
                f"{r['compensation_ngonka']},{r['compensation_gonka']:.4f}\n"
            )
    print(f"\nSaved to {csv_file}")

    output = {
        "epoch": EPOCH,
        "criteria": {
            "cpoc1_ratio_gt": CPOC1_MIN_RATIO,
            "final_ratio_lt": FINAL_MAX_RATIO,
            "actual_rewards": 0,
        },
        "baseline_rate_ngonka_per_weight": baseline_rate,
        "healthy_participants": len(healthy),
        "affected_participants": len(affected),
        "total_compensation_ngonka": int(total_compensation),
        "total_compensation_gonka": total_compensation / 1e9,
        "compensation": results,
    }
    json_file = os.path.join(os.path.dirname(__file__), "compensation.json")
    with open(json_file, "w") as f:
        json.dump(output, f, indent=2)
    print(f"Saved to {json_file}")


if __name__ == "__main__":
    main()
