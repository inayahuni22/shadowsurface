import csv
import random
from pathlib import Path

from load_network import load_network

import sys
SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 42
random.seed(SEED)

OUT_FILE = Path(__file__).parent / f"flows_{SEED}.csv"

# Typical daily bytes per rule: (min, max)
VOLUME = {"iot": (500, 5_000), "default": (5_000, 500_000)}


def generate_normal_flows(graph, days=8):
    flows = []
    for day in range(days):
        for u, v, data in graph.edges(data=True):
            zone = graph.nodes[u]["zone"]
            low, high = VOLUME["iot"] if zone == "iot" else VOLUME["default"]
            for _ in range(random.randint(20, 40)):
                flows.append({
                    "day": day,
                    "hour": random.randint(7, 19),
                    "source": u,
                    "destination": v,
                    "port": random.choice(data["ports"]),
                    "bytes": random.randint(low, high),
                    "label": "normal",
                })
    return flows

def generate_attack_flows():
    """Labelled attack scenarios, all on day 7 (after the normal week)."""
    return [
        # Exfiltration: aquarium sends 10 GB to the internet at 3am
        {"day": 7, "hour": 3, "source": "iot_aquarium", "destination": "internet",
         "port": 443, "bytes": 10_000_000_000, "label": "exfiltration"},
        # Lateral movement: camera probes the database directly
        {"day": 7, "hour": 2, "source": "iot_camera_lobby", "destination": "db_customer",
         "port": 5432, "bytes": 40_000, "label": "lateral_movement"},
        # Unexpected port: HVAC sensor talks to the API on SSH
        {"day": 7, "hour": 4, "source": "iot_hvac", "destination": "server_api",
         "port": 22, "bytes": 8_000, "label": "unexpected_port"},
        # Volume spike: printer pushes far more than usual to the file server
        {"day": 7, "hour": 14, "source": "printer_office", "destination": "server_files",
         "port": 445, "bytes": 900_000_000, "label": "volume_spike"},
    ]

def generate_attack_batch(n=50):
    """Randomised attacks on day 7. Some are subtle on purpose."""
    attacks = []
    iot = ["iot_aquarium", "iot_camera_lobby", "iot_hvac", "iot_badge_reader", "iot_sensor_warehouse"]
    for _ in range(n):
        kind = random.choice(["blatant", "business_hours", "slow_exfil"])
        src = random.choice(iot)
        if kind == "blatant":
            attacks.append({"day": 7, "hour": random.randint(0, 5), "source": src,
                            "destination": "db_customer", "port": 5432,
                            "bytes": random.randint(10_000, 200_000), "label": "blatant"})
        elif kind == "business_hours":
            attacks.append({"day": 7, "hour": random.randint(9, 17), "source": src,
                            "destination": "db_customer", "port": 5432,
                            "bytes": random.randint(10_000, 200_000), "label": "business_hours"})
        else:
            attacks.append({"day": 7, "hour": random.randint(9, 17), "source": src,
                            "destination": "server_api", "port": 443,
                            "bytes": random.randint(8_000, 20_000), "label": "slow_exfil"})
    return attacks

def generate_stealth_attacks(n=30):
    """Low-and-slow attacks that mimic normal traffic."""
    attacks = []
    iot = ["iot_aquarium", "iot_camera_lobby", "iot_hvac", "iot_badge_reader", "iot_sensor_warehouse"]
    targets = random.sample(iot, 2)
    for _ in range(n):
        attacks.append({"day": 7, "hour": random.randint(9, 17),
                        "source": random.choice(targets),
                        "destination": "server_api", "port": 443,
                        "bytes": random.randint(3_000, 5_000),
                        "label": "stealth"})
    return attacks

if __name__ == "__main__":
    g = load_network()
    flows = generate_normal_flows(g) + generate_attack_batch() + generate_stealth_attacks()
    with open(OUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=flows[0].keys())
        writer.writeheader()
        writer.writerows(flows)
    print(f"Wrote {len(flows)} flows")