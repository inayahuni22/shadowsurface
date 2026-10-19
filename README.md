# ShadowSurface

**A defensive IoT security analysis project: find the hidden attack paths created by overlooked connected devices, detect suspicious behaviour, and measure what network segmentation actually fixes.**

> Simulation only. All networks, devices and traffic are synthetic. No real systems are scanned or attacked.

## Why this project exists

Organisations often secure their computers while overlooking the connected devices on the same network: aquariums, cameras, printers, sensors, badge readers. The 2017 casino fish-tank incident, reported by Darktrace, is the well-known example of an IoT device being used as an entry point. The public technical details are incomplete, so this project does **not** attempt to reproduce that attack. It uses the idea as inspiration for a general defensive question:

> How effectively can network-graph analysis and behavioural anomaly detection identify and contain attack paths originating from overlooked IoT devices?

## What it does

1. **Models a network** (21 nodes, 21 allowed connections) from a JSON definition, as a directed graph in NetworkX.
2. **Finds attack paths** from every low-trust device to sensitive assets (`db_customer`, `db_finance`, `server_files`).
3. **Simulates segmentation** and compares strategies by risk removed versus legitimate business rules broken.
4. **Generates synthetic traffic** (8 days of normal flows plus labelled attacks) and runs three detectors over it.
5. **Evaluates** the detectors across 5 random seeds with precision, recall and false positives.
6. **Serves everything over a FastAPI backend** to a React dashboard.

## Architecture

```
network.json -> load_network.py -> NetworkX digraph
                     |-> attack_paths.py   (reachability, shortest paths)
                     |-> segmentation.py   (blocks, minimum cut, ingest gateway)
traffic.py -> flows_<seed>.csv -> detector.py -> evaluate_seeds.py
                     |
                  api.py (FastAPI) -> React dashboard (React Flow)
```

All security logic lives in Python. The frontend only displays what the API returns and computes no risk or detection results of its own.

## Results

### 1. Attack paths

In the original network, **6 of 8 low-trust devices** can reach a sensitive asset: the aquarium controller, lobby camera, HVAC sensor, badge reader and warehouse sensor via `server_api`, and the office printer directly to `server_files` over SMB. `server_api` is the chokepoint: it can reach both databases and the file server, and five IoT devices are allowed to talk to it.

### 2. Segmentation strategies

| Strategy | Risky devices | Rules broken | Legitimate rules broken |
|---|---|---|---|
| None (baseline) | 6 | 0 | 0 |
| Zone blocks (IoT -> API, office -> files) | 0 | 7 | 5 |
| Minimum cut (unweighted) | 0 | 4 | 2 |
| Minimum cut (with business-cost weights) | 0 | 4 | 2 |
| Isolated IoT ingest gateway + 2 lab rules removed | 0 | 2 removed, 6 rewired | 0 |

Findings:

- Deleting rules alone cannot fix this network. Cutting the IoT-to-API rules costs more business function than cutting the API's onward access, and both break something legitimate.
- Adding business-cost weights to the minimum cut did not change its answer, because every option still breaks an essential rule.
- The structural fix is an **ingest gateway**: IoT telemetry still has a destination, but that destination has no path to sensitive assets.

### 3. Detection

Evaluated on 5 seeds. Each seed contains 8 days of normal traffic and 80 attack flows on day 7 (50 detectable by simple checks, 30 deliberately "stealth": allowed rule, allowed port, business hours, normal byte count). Baselines are learned from days 0 to 6 only.

| Detector | Unit | Recall | False positives |
|---|---|---|---|
| Rules + per-flow volume (z-score) | flow | 62.5% (precision 100%) | 0 |
| Daily flow count above normal max | device-day | 56.5% (13 of 23) | 0 |
| Daily bytes above normal max (IoT only) | device-day | 91.3% (21 of 23) | 1 |
| Daily bytes with a 125% margin | device-day | 60.9% (14 of 23) | 0 |

Findings:

- Rules and volume catch every non-stealth attack with no false alarms, and **miss all 30 stealth flows per seed**. No per-flow check can separate them, because they look like normal traffic.
- Per-flow alerting on a count signal collapsed precision to 26%, because a daily count cannot say which flows are the attack. Scoring at the device-day level fixed the unit, not just the number.
- Daily bytes was the strongest signal. Adding a blanket 125% margin removed the false positive but cost about 30 points of recall, so it was not used.

## Limitations

Read these before trusting any number above.

- **Synthetic, uniform traffic.** Normal flows are drawn from fixed uniform ranges. Real traffic is burstier and messier. The "above historical max" thresholds are effectively tuned to this generator.
- **Author-written attacks.** I wrote both the attacks and the detectors. A high score shows the detector handles these scenarios, not that it generalises.
- **Small device-level sample.** 23 of the 25 scored device-days are attacked, so only 2 are clean. The false-positive rate at device level is therefore barely measured (1 false positive in 2 clean device-days). Treat 91.3% recall as roughly 80 to 95%, and the false-alarm rate as unknown.
- **Scope is IoT only.** The daily bytes detector is limited to `iot_*` sources. Run across every source pair, it also flagged three non-IoT pairs (HR to file server, API to customer database, gateway to security monitor) that were not attacked. It does not watch workstations or servers.
- **The ingest gateway has no outbound rules.** That is why it scores 0 risky devices. A real gateway must forward telemetry somewhere, and that onward path would need locking down.
- **Attack-path model is reachability only.** It treats every allowed rule as exploitable. It models neither vulnerabilities nor credentials nor protocol detail.
- **Limited testing.** The 3 pytest tests cover the segmentation result and that essential rules survive. The detectors are validated by the evaluation scripts, not unit tests.
- **Seed dependence.** Results vary slightly by seed, so report the 5-seed totals, not a single run.

## Run it (Windows, PowerShell)

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install networkx fastapi uvicorn pytest

# generate traffic for seeds 1 to 5
1..5 | ForEach-Object { python traffic.py $_ }

# reproduce the results
python attack_paths.py
python segmentation.py
python evaluate_seeds.py
pytest

# start the API
uvicorn api:app --reload
```

If PowerShell blocks the activate script: `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`.

## API

| Endpoint | Returns |
|---|---|
| `GET /summary?seed=1` | Headline counts for the dashboard |
| `GET /network` | Original nodes and edges |
| `GET /network/segmented` | Nodes and edges after segmentation (includes `iot_ingest`) |
| `GET /attack-paths/{device_id}` | Paths from a compromised device to sensitive assets |
| `GET /attack-paths/{device_id}/segmented` | Same, after segmentation |
| `GET /segmentation/summary` | Risky devices before and after |
| `GET /alerts?seed=1` | Flow alerts and device alerts (ground-truth labels removed) |

Full shapes are in [`API_SPEC.md`](API_SPEC.md). CORS is open (`*`) for local demos and should be restricted before any public hosting.

## Frontend and AI-tool disclosure

The dashboard UI (React, TypeScript, Tailwind, React Flow) was **scaffolded with Lovable** from a prompt I wrote against the API spec above. The interaction design (compromise simulation, before/after toggle, remediated markers) and the reviewing and testing of its behaviour against the API are mine. The network model, attack-path analysis, segmentation logic, traffic simulator, detectors, evaluation and API are written and verified by me in Python. The frontend lives in its own repository: *(https://network-before-after-atlas.lovable.app)*.

## Repository layout

```
backend/
  network.json          network definition (devices and rules)
  load_network.py       JSON -> NetworkX digraph
  attack_paths.py       reachability and shortest paths
  segmentation.py       blocks, minimum cut, ingest gateway
  traffic.py            seeded traffic and attack generator
  detector.py           rules, volume, daily count, daily bytes detectors
  evaluate_seeds.py     5-seed evaluation
  api.py                FastAPI endpoints
  test_segmentation.py  pytest tests
API_SPEC.md             response shapes for the frontend
```

## Possible next steps

- Validate the detectors on a public IoT dataset (for example CIC-IoT-2023) instead of only synthetic traffic.
- Compare against Isolation Forest.
- Give the ingest gateway a restricted onward path and re-check reachability.
- Tag findings to MITRE ATT&CK (lateral movement, exfiltration).
- Generate more clean device-days to measure the false-positive rate properly.
