from load_network import load_network
from segmentation import (
    add_ingest_gateway,
    block_edge,
    broken_rules,
    risky_devices,
)


def build_fixed():
    before = load_network()
    iot = [n for n, d in before.nodes(data=True) if d["zone"] == "iot"]
    fixed = add_ingest_gateway(before, iot)
    fixed = block_edge(fixed, "server_api", "db_finance")
    fixed = block_edge(fixed, "printer_office", "server_files")
    return before, fixed


def test_original_network_is_risky():
    before, _ = build_fixed()
    assert len(risky_devices(before)) == 6


def test_fixed_network_has_no_risky_devices():
    _, fixed = build_fixed()
    assert risky_devices(fixed) == []


def test_essential_rules_survive():
    _, fixed = build_fixed()
    assert fixed.has_edge("server_api", "db_customer")
    assert fixed.has_edge("server_api", "server_files")
    assert fixed.has_edge("workstation_hr", "server_files")