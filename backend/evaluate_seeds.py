from collections import Counter

from detector import (build_baselines, detect, detect_daily_bytes,
                      detect_daily_count, detect_volume, load_flows,
                      merge_alerts)
from load_network import load_network

g = load_network()
SEEDS = [1, 2, 3, 4, 5]
ATTACK_LABELS = ("stealth", "slow_exfil")

totals = Counter()
dev_tp = dev_fp = dev_fn = 0
bytes_tp = bytes_fp = bytes_fn = 0

for seed in SEEDS:
    flows = load_flows(seed)

    # Per-flow detectors (rules + volume only)
    alerts = merge_alerts(detect(flows, g) + detect_volume(flows, build_baselines(flows)))
    attacks = [f for f in flows if f["label"] != "normal"]
    caught = [a for a in alerts if a["label"] != "normal"]
    totals["tp"] += len(caught)
    totals["fp"] += sum(1 for a in alerts if a["label"] == "normal")
    totals["fn"] += len(attacks) - len(caught)

    # Shared ground truth for both device-level detectors
    day7 = [f for f in flows if f["day"] == 7]
    attacked = {f["source"] for f in day7
                if f["label"] in ATTACK_LABELS and f["destination"] == "server_api"}
    candidates = {f["source"] for f in day7
                  if f["destination"] == "server_api" and f["source"].startswith("iot_")}

    # Device-level count detector
    flagged = {a["source"] for a in detect_daily_count(flows)
               if a["destination"] == "server_api"} & candidates
    dev_tp += len(flagged & attacked)
    dev_fp += len(flagged - attacked)
    dev_fn += len(attacked - flagged)

    # Device-level bytes detector
    flagged = {a["source"] for a in detect_daily_bytes(flows)
               if a["destination"] == "server_api"} & candidates
    bytes_tp += len(flagged & attacked)
    bytes_fp += len(flagged - attacked)
    bytes_fn += len(attacked - flagged)

tp, fp, fn = totals["tp"], totals["fp"], totals["fn"]
print(f"Per-flow (rules + volume), {len(SEEDS)} seeds")
print(f"  Precision: {tp / (tp + fp):.2%}")
print(f"  Recall:    {tp / (tp + fn):.2%}\n")

print("Device-level count detector")
print(f"  Devices caught:  {dev_tp} of {dev_tp + dev_fn}")
print(f"  False positives: {dev_fp}")
print(f"  Recall:          {dev_tp / (dev_tp + dev_fn):.2%}\n")

print("Device-level bytes detector")
print(f"  Devices caught:  {bytes_tp} of {bytes_tp + bytes_fn}")
print(f"  False positives: {bytes_fp}")
print(f"  Recall:          {bytes_tp / (bytes_tp + bytes_fn):.2%}")