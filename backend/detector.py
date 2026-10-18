import csv
from pathlib import Path

from load_network import load_network

FLOWS_FILE = Path(__file__).parent / "flows.csv"


def load_flows(seed=None):
    path = FLOWS_FILE if seed is None else FLOWS_FILE.parent / f"flows_{seed}.csv"
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["day"] = int(r["day"])
        r["hour"] = int(r["hour"])
        r["port"] = int(r["port"])
        r["bytes"] = int(r["bytes"])
    return rows


def detect(flows, graph):
    alerts = []
    for fl in flows:
        src, dst = fl["source"], fl["destination"]
        reasons = []

        if not graph.has_edge(src, dst):
            reasons.append("destination not in allowed rules")
        elif fl["port"] not in graph.edges[src, dst]["ports"]:
            reasons.append("port not allowed for this rule")

        if fl["hour"] < 6 or fl["hour"] > 20:
            reasons.append("outside business hours")

        if reasons:
            alerts.append({**fl, "reasons": reasons})
    return alerts


def build_baselines(flows):
    """Mean and standard deviation of bytes per (source, destination) pair, from normal days only."""
    from statistics import mean, pstdev

    groups = {}
    for fl in flows:
        if fl["day"] < 7:
            groups.setdefault((fl["source"], fl["destination"]), []).append(fl["bytes"])
    return {k: (mean(v), pstdev(v)) for k, v in groups.items()}


def detect_volume(flows, baselines, threshold=4):
    alerts = []
    for fl in flows:
        key = (fl["source"], fl["destination"])
        if key not in baselines:
            continue
        avg, std = baselines[key]
        if std > 0 and (fl["bytes"] - avg) / std > threshold:
            alerts.append({**fl, "reasons": [f"volume {fl['bytes']:,} bytes is far above normal"]})
    return alerts


def merge_alerts(alerts):
    """One alert per flow, with every reason combined."""
    merged = {}
    for a in alerts:
        key = (a["day"], a["hour"], a["source"], a["destination"], a["port"], a["bytes"])
        if key in merged:
            merged[key]["reasons"] += a["reasons"]
        else:
            merged[key] = {**a, "reasons": list(a["reasons"])}
    return list(merged.values())


def detect_daily_count(flows, margin=1.0):
    """Flag a device whose flow count to a destination on day 7 exceeds its normal daily max."""
    from collections import Counter

    daily = Counter((f["day"], f["source"], f["destination"]) for f in flows)
    normal_max = {}
    for (day, src, dst), count in daily.items():
        if day < 7:
            normal_max[(src, dst)] = max(normal_max.get((src, dst), 0), count)

    flagged = {k for k, c in daily.items()
               if k[0] == 7 and (k[1], k[2]) in normal_max
               and c > normal_max[(k[1], k[2])] * margin}

    alerts = []
    for fl in flows:
        if fl["day"] == 7 and (7, fl["source"], fl["destination"]) in flagged:
            alerts.append({**fl, "reasons": ["daily flow count above normal maximum"]})
    return alerts


def detect_daily_bytes(flows, margin=1.0, iot_only=True):
    """Flag a device whose day-7 bytes to a destination exceed its normal daily max."""
    from collections import defaultdict

    daily = defaultdict(int)
    for f in flows:
        daily[(f["day"], f["source"], f["destination"])] += f["bytes"]

    normal_max = {}
    for (day, src, dst), total in daily.items():
        if day < 7:
            normal_max[(src, dst)] = max(normal_max.get((src, dst), 0), total)

    return [
        {"day": 7, "source": src, "destination": dst, "bytes": total,
         "reasons": [f"daily bytes {total:,} above normal max {normal_max[(src, dst)]:,}"]}
        for (day, src, dst), total in daily.items()
        if day == 7 and (src, dst) in normal_max
        and total > normal_max[(src, dst)] * margin
        and (not iot_only or src.startswith("iot_"))
    ]


if __name__ == "__main__":
    g = load_network()
    flows = load_flows()
    baselines = build_baselines(flows)
    alerts = merge_alerts(detect(flows, g) + detect_volume(flows, baselines))
    print(f"Flows checked: {len(flows)}")
    print(f"Alerts raised: {len(alerts)}\n")
    for a in alerts:
        print(f"{a.get('label', ''):17} {a['source']} -> {a['destination']}  {a['reasons']}")