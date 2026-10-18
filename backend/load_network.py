import json
from pathlib import Path

import networkx as nx

DATA_FILE = Path(__file__).parent / "network.json"


def load_network():
    with open(DATA_FILE, encoding="utf-8") as f:
        data = json.load(f)

    graph = nx.DiGraph()

    for d in data["devices"]:
        graph.add_node(d["id"], **d)

    for rule in data["communication_rules"]:
        if rule["allowed"]:
            graph.add_edge(
                rule["source"],
                rule["destination"],
                ports=rule["ports"],
                protocol=rule["protocol"],
                reason=rule["reason"],
            )

    return graph


if __name__ == "__main__":
    g = load_network()
    print(f"Devices: {g.number_of_nodes()}")
    print(f"Allowed connections: {g.number_of_edges()}")