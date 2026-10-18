from collections import Counter

from detector import (build_baselines, detect, detect_volume, load_flows,
                      merge_alerts)
from load_network import load_network

g = load_network()
flows = load_flows()
from detector import detect_daily_count
alerts = merge_alerts(detect(flows, g) + detect_volume(flows, build_baselines(flows)) + detect_daily_count(flows))

attacks = Counter(f["label"] for f in flows if f["label"] != "normal")
caught = Counter(a["label"] for a in alerts if a["label"] != "normal")
false_pos = sum(1 for a in alerts if a["label"] == "normal")

tp = sum(caught.values())
fn = sum(attacks.values()) - tp
precision = tp / (tp + false_pos) if tp + false_pos else 0
recall = tp / (tp + fn) if tp + fn else 0

print(f"True positives:  {tp}")
print(f"False positives: {false_pos}")
print(f"False negatives: {fn}")
print(f"Precision: {precision:.2%}")
print(f"Recall:    {recall:.2%}\n")
for label, total in attacks.items():
    print(f"{label:16} caught {caught[label]}/{total}")