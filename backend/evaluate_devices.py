from detector import detect_daily_count, load_flows

flows = load_flows()
day7 = [f for f in flows if f["day"] == 7]

# Devices that actually sent stealth traffic (ground truth)
attacked = {f["source"] for f in day7 if f["label"] == "stealth"}

# Devices the count detector flagged
flagged = {a["source"] for a in detect_daily_count(flows)}

# Only judge devices that send to server_api, since that's where stealth happens
candidates = {f["source"] for f in day7 if f["destination"] == "server_api"}

tp = len(flagged & attacked)
fp = len((flagged & candidates) - attacked)
fn = len(attacked - flagged)

print(f"Devices attacked:  {sorted(attacked)}")
print(f"Devices flagged:   {sorted(flagged & candidates)}\n")
print(f"True positives:  {tp}")
print(f"False positives: {fp}")
print(f"False negatives: {fn}")