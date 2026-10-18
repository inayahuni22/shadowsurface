from collections import Counter

from detector import load_flows

flows = load_flows()
day7 = [f for f in flows if f["day"] == 7]

per_device = Counter(f["source"] for f in day7 if f["destination"] == "server_api")
normal_days = Counter(
    (f["day"], f["source"]) for f in flows
    if f["day"] < 7 and f["destination"] == "server_api"
)

print("Day 7 flows to server_api, per device:")
for device, count in per_device.items():
    print(f"  {device:22} {count}")

print("\nNormal daily flows to server_api, per device (days 0-6):")
by_device = {}
for (day, device), count in normal_days.items():
    by_device.setdefault(device, []).append(count)
for device, counts in by_device.items():
    print(f"  {device:22} min {min(counts)}  max {max(counts)}")