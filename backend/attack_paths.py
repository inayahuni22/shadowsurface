import networkx as nx

from load_network import load_network

SENSITIVE = ["db_customer", "db_finance", "server_files"]


def find_paths(graph, source, targets):
    results = {}
    for target in targets:
        if nx.has_path(graph, source, target):
            results[target] = nx.shortest_path(graph, source, target)
        else:
            results[target] = None
    return results

if __name__ == "__main__":
    g = load_network()
    low_trust = [n for n, d in g.nodes(data=True) if d["trust"] == "low"]
    print(f"Checking {len(low_trust)} low-trust devices\n")
    for source in low_trust:
        paths = find_paths(g, source, SENSITIVE)
        reachable = [t for t, p in paths.items() if p]
        status = "RISKY" if reachable else "ok"
        print(f"{status:6} {source:22} reaches: {reachable or 'nothing sensitive'}")