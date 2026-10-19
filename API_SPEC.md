# ShadowSurface API (http://127.0.0.1:8000)

GET /summary?seed=1
-> {device_count, connection_count, risky_before, risky_after, flow_alert_count, device_alert_count}

GET /network
-> {nodes: [{id, name, type, zone, trust, criticality}],
    edges: [{source, destination, ports, protocol, reason}]}

GET /network/segmented
-> same shape as /network, after segmentation (includes the iot_ingest node)

GET /attack-paths/{device_id}
-> {device, paths: [{target, path: [device ids] | null, reachable}]}

GET /attack-paths/{device_id}/segmented
-> same shape, computed after segmentation

GET /segmentation/summary
-> {risky_before: [device ids], risky_after: [device ids]}

GET /alerts?seed=1
-> {seed, flow_alerts: [{day, hour, source, destination, port, bytes, reasons}],
    device_alerts: [{day, source, destination, bytes, reasons}]}