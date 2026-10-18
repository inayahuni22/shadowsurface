from collections import defaultdict

from detector import load_flows

normal_totals = defaultdict(list)
day7_totals = {}
attacked = set()

for seed in [1, 2, 3, 4, 5]:
    flows = load_flows(seed)
    daily = defaultdict(int)
    for f in flows:
        if (f["destination"] == "server_api" and f["source"].startswith("iot_")
        and f["label"] in ("normal", "stealth")):
            daily[(f["day"], f["source"])] += f["bytes"]
            if f["day"] == 7 and f["label"] == "stealth":
                attacked.add((seed, f["source"]))
    for (day, src), total in daily.items():
        if day < 7:
            normal_totals[src].append(total)
        else:
            day7_totals[(seed, src)] = total

print("Normal daily bytes to server_api, per device (min / max):")
for src, vals in normal_totals.items():
    print(f"  {src:22} {min(vals):>9,} / {max(vals):>9,}")

above = sum(1 for k in attacked if day7_totals[k] > max(normal_totals[k[1]]))
print(f"\nAttacked device-days above normal max: {above} of {len(attacked)}")

clean = [k for k in day7_totals if k not in attacked]
false_above = sum(1 for k in clean if day7_totals[k] > max(normal_totals[k[1]]))
print(f"Clean device-days above normal max:    {false_above} of {len(clean)}")