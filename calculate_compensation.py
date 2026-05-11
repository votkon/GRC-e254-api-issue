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
import math
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

# Tokenomics: epoch reward pool = initial_epoch_reward * exp(decay_rate * (epoch - genesis_epoch))
INITIAL_EPOCH_REWARD = 323_000_000_000_000  # ngonka
DECAY_RATE = -475e-6
GENESIS_EPOCH = 1


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
    """Returns members from epoch group data with cw/weight ratio and dropout flag."""
    d = run_cli(["query", "inference", "show-epoch-group-data", str(EPOCH)], height=height)
    if not d:
        return {}
    vw = d.get("epoch_group_data", d).get("validation_weights", [])
    result = {}
    for x in vw:
        addr = x["member_address"]
        weight = int(x.get("weight", 0))
        cw = int(x["confirmation_weight"]) if "confirmation_weight" in x else None
        ratio = cw / weight if (cw is not None and weight > 0) else None
        dropped = cw is None  # no confirmation_weight = dropped from CPoC
        result[addr] = {"weight": weight, "ratio": ratio, "dropped": dropped}
    return result


def get_final_conf_ratio(address):
    """Returns confirmationPoCRatio from show-participant at epoch end.
    Only meaningful when the participant was not dropped (has confirmation_weight).
    """
    d = run_cli(["query", "inference", "show-participant", address], height=EPOCH_END_HEIGHT)
    if not d:
        return None
    ratio = d.get("participant", {}).get("current_epoch_stats", {}).get("confirmationPoCRatio", {})
    value = ratio.get("value")
    if value is None:
        return None
    exponent = int(ratio.get("exponent", 0))
    return int(value) * (10 ** exponent)


def get_rewards(address):
    d = run_cli([
        "query", "inference",
        "show-epoch-performance-summary-by-participant",
        str(EPOCH), address
    ])
    if not d:
        return 0
    return int(d.get("epochPerformanceSummary", {}).get("rewarded_coins", 0))


def main():
    print("Loading pre-computed participant data...", flush=True)
    data_file = os.path.join(os.path.dirname(__file__), "epoch254_participants.json")
    with open(data_file) as f:
        participants_map = {p["address"]: p for p in json.load(f)}

    print("Loading epoch members at CPoC1...", flush=True)
    members_cpoc1 = get_epoch_members(CPOC1_HEIGHT)
    print("Loading epoch members at epoch end...", flush=True)
    members_final = get_epoch_members(EPOCH_END_HEIGHT)

    healthy = []
    affected = []

    total = len(members_cpoc1)
    for i, (addr, e1) in enumerate(members_cpoc1.items(), 1):
        print(f"  [{i}/{total}] {addr}", flush=True)
        r1 = e1["ratio"]
        if r1 is None:
            continue

        e_final = members_final.get(addr)
        final_dropped = e_final is None or e_final["dropped"]

        if final_dropped:
            r_final = 0.0
        else:
            r_final = get_final_conf_ratio(addr)
            if r_final is None:
                r_final = 0.0

        actual_rewards = participants_map.get(addr, {}).get("rewarded_ngonka", 0)
        weight = int(e1.get("weight", 0))

        ratio_criteria = r1 > CPOC1_MIN_RATIO and r_final < FINAL_MAX_RATIO and actual_rewards == 0
        dropped_criteria = r1 > CPOC1_MIN_RATIO and final_dropped and actual_rewards == 0

        if ratio_criteria or dropped_criteria:
            affected.append({
                "address": addr,
                "weight": weight,
                "cpoc1_ratio": r1,
                "final_ratio": r_final,
                "actual_rewards_ngonka": actual_rewards,
            })
        elif r1 > CPOC1_MIN_RATIO and actual_rewards > 0 and not final_dropped:
            healthy.append({
                "address": addr,
                "weight": weight,
                "conf_ratio": r_final,
                "rewards_ngonka": actual_rewards,
            })

    total_healthy_weight = sum(p["weight"] for p in healthy)
    total_healthy_rewards = sum(p["rewards_ngonka"] for p in healthy)

    # Chain reward formula: weight / total_epoch_weight * epoch_theoretical_reward
    epoch_theoretical_reward = INITIAL_EPOCH_REWARD * math.exp(DECAY_RATE * (EPOCH - GENESIS_EPOCH))
    total_epoch_weight = sum(e["weight"] for e in members_cpoc1.values())

    print(f"\nHealthy participants (CPoC1>45.5%, not dropped, rewarded): {len(healthy)}")
    print(f"  Total weight  : {total_healthy_weight:,}")
    print(f"  Total rewards : {total_healthy_rewards / 1e9:,.2f} GONKA")
    print(f"\nEpoch 254 theoretical reward pool : {epoch_theoretical_reward / 1e9:,.6f} GONKA")
    print(f"Total epoch weight                : {total_epoch_weight:,}")

    print(f"\nAffected participants (CPoC1>45.5%, final<45.5%, rewards=0): {len(affected)}")

    results = []
    total_compensation = 0

    for p in affected:
        compensation = p["weight"] / total_epoch_weight * epoch_theoretical_reward
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
        "epoch_theoretical_reward_ngonka": int(epoch_theoretical_reward),
        "epoch_theoretical_reward_gonka": epoch_theoretical_reward / 1e9,
        "total_epoch_weight": total_epoch_weight,
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
