from attack_paths import SENSITIVE, find_paths
from load_network import load_network
import networkx as nx

def apply_block(graph, source_zone, destination):
    """Remove every edge from devices in source_zone to the destination."""
    segmented = graph.copy()
    to_remove = [
        (u, v)
        for u, v in segmented.edges()
        if v == destination and segmented.nodes[u]["zone"] == source_zone
    ]
    segmented.remove_edges_from(to_remove)
    return segmented


def risky_devices(graph):
    low_trust = [n for n, d in graph.nodes(data=True) if d["trust"] == "low"]
    return [
        n for n in low_trust
        if any(find_paths(graph, n, SENSITIVE).values())
    ]
def broken_rules(original, segmented):
    """Rules that existed before but are gone after segmentation."""
    return [
        (u, v, original.edges[u, v]["reason"])
        for u, v in original.edges()
        if not segmented.has_edge(u, v)
    ]
def block_edge(graph, source, destination):
    """Remove one specific rule."""
    segmented = graph.copy()
    if segmented.has_edge(source, destination):
        segmented.remove_edge(source, destination)
    return segmented

# Rules the business depends on get a high cost; everything else costs 1.
ESSENTIAL = {
    ("server_api", "db_customer"),
    ("server_api", "server_files"),
    ("workstation_hr", "server_files"),
    ("iot_camera_lobby", "server_api"),
    ("iot_hvac", "server_api"),
    ("iot_badge_reader", "server_api"),
    ("iot_sensor_warehouse", "server_api"),
}


def minimum_cut_rules(graph, sources, targets):
    """Cheapest set of rules to cut, avoiding essential business rules."""
    g = graph.copy()
    for u, v in g.edges():
        g.edges[u, v]["capacity"] = 100 if (u, v) in ESSENTIAL else 1
    for s in sources:
        g.add_edge("SUPER_SOURCE", s, capacity=10000)
    for t in targets:
        g.add_edge(t, "SUPER_TARGET", capacity=10000)
    cut_value, (reachable, non_reachable) = nx.minimum_cut(
        g, "SUPER_SOURCE", "SUPER_TARGET"
    )
    return [
        (u, v)
        for u in reachable
        for v in g[u]
        if v in non_reachable and u != "SUPER_SOURCE" and v != "SUPER_TARGET"
    ]

def add_ingest_gateway(graph, iot_sources):
    """Rewire IoT -> server_api rules through an isolated ingest gateway."""
    g = graph.copy()
    g.add_node(
        "iot_ingest", id="iot_ingest", name="IoT Ingest Gateway",
        type="gateway", zone="dmz", trust="high", criticality="medium",
    )
    for s in iot_sources:
        if g.has_edge(s, "server_api"):
            reason = g.edges[s, "server_api"]["reason"]
            g.remove_edge(s, "server_api")
            g.add_edge(s, "iot_ingest", ports=[443], protocol="TCP", reason=reason)
    return g


if __name__ == "__main__":
    before = load_network()
    iot = [n for n, d in before.nodes(data=True) if d["zone"] == "iot"]

    fixed = add_ingest_gateway(before, iot)
    fixed = block_edge(fixed, "server_api", "db_finance")
    fixed = block_edge(fixed, "printer_office", "server_files")

    print(f"Risky devices before: {len(risky_devices(before))}")
    print(f"Risky devices after:  {len(risky_devices(fixed))}")
    print(f"Still risky: {risky_devices(fixed)}")