from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from attack_paths import SENSITIVE, find_paths
from segmentation import add_ingest_gateway, block_edge, risky_devices
from load_network import load_network
from detector import (build_baselines, detect, detect_daily_bytes,
                      detect_volume, load_flows, merge_alerts)

app = FastAPI(title="ShadowSurface API")

# Allow the frontend (Lovable) to call this API from the browser
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/network")
def get_network():
    g = load_network()
    nodes = [dict(d) for _, d in g.nodes(data=True)]
    edges = [
        {"source": u, "destination": v, "ports": d["ports"],
         "protocol": d["protocol"], "reason": d["reason"]}
        for u, v, d in g.edges(data=True)
    ]
    return {"nodes": nodes, "edges": edges}

@app.get("/attack-paths/{device_id}")
def get_attack_paths(device_id: str):
    g = load_network()
    if device_id not in g:
        raise HTTPException(status_code=404, detail="Unknown device")
    paths = find_paths(g, device_id, SENSITIVE)
    return {
        "device": device_id,
        "paths": [
            {"target": t, "path": p, "reachable": p is not None}
            for t, p in paths.items()
        ],
    }

def build_fixed_network():
    g = load_network()
    iot = [n for n, d in g.nodes(data=True) if d["zone"] == "iot"]
    fixed = add_ingest_gateway(g, iot)
    fixed = block_edge(fixed, "server_api", "db_finance")
    fixed = block_edge(fixed, "printer_office", "server_files")
    return g, fixed


@app.get("/attack-paths/{device_id}/segmented")
def get_segmented_paths(device_id: str):
    _, fixed = build_fixed_network()
    if device_id not in fixed:
        raise HTTPException(status_code=404, detail="Unknown device")
    paths = find_paths(fixed, device_id, SENSITIVE)
    return {
        "device": device_id,
        "paths": [
            {"target": t, "path": p, "reachable": p is not None}
            for t, p in paths.items()
        ],
    }


@app.get("/segmentation/summary")
def segmentation_summary():
    before, after = build_fixed_network()
    return {
        "risky_before": risky_devices(before),
        "risky_after": risky_devices(after),
    }

def strip_label(alerts):
    return [{k: v for k, v in a.items() if k != "label"} for a in alerts]

@app.get("/alerts")
def get_alerts(seed: int = 1):
    g = load_network()
    flows = load_flows(seed)
    flow_alerts = merge_alerts(detect(flows, g) + detect_volume(flows, build_baselines(flows)))
    device_alerts = detect_daily_bytes(flows)
    return {
        "seed": seed,
        "flow_alerts": strip_label(flow_alerts),
        "device_alerts": device_alerts,
    }