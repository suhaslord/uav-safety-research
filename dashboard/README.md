# AegisLand Research Cockpit

The cockpit is a local, dependency-free interface for inspecting Phase 7 **simulation-only development evidence**. It is an analysis surface, not a vehicle-control interface.

## Run locally

From the repository root:

```bash
python scripts/serve_dashboard.py
```

Open `http://127.0.0.1:8765` in a browser.

## Load a result bundle

Use the two file cards in the interface:

1. Load `summary.csv` from a Phase 7 result directory.
2. Optionally load `paired_plant_effects.csv` from the same directory.

The cockpit then lets you filter by image condition, fault scenario, and plant model. It displays success, unsafe touchdown, abort, reference availability, the legacy-vs-stronger-plant comparison, and a condition × fault unsafe-touchdown matrix.

## Interpretation

The interface deliberately keeps Phase 7 development results separate from the frozen Phase 6B claim. A zero observed unsafe-touchdown rate in a small development cell is not evidence of zero real risk. Common-mode failures and plant-model sensitivity should remain visible rather than being tuned away.

No external JavaScript libraries, services, or telemetry are used. Data remains in the browser session.
