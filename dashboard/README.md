# AegisLand Research Cockpit

The Research Cockpit is the browser interface for the AegisLand simulation-only research prototype. It is designed to make the evidence trail easier to inspect without turning the project into a vehicle-control UI or hiding unfavorable results behind a single pass/fail score.

## What the cockpit shows

The main page, `dashboard/index.html`, summarizes the research progression from the frozen Phase 6B synthetic benchmark through Phase 7 external-validity stress testing, the preserved Phase 8 PX4/Gazebo `diagnostic_mismatch`, and the first valid Phase 9 genuine-camera trace.

The Phase 9 view keeps both sides of the result visible: strong detection availability on the seen trace and the much weaker PnP metric geometry. It also exposes evidence identity, workflow/artifact references, raw-evidence hashes, and the claim boundaries that remain in force.

The original Phase 7 result explorer is retained at `dashboard/phase7.html`. It can load a local `dashboard_bundle.json`, `summary.csv`, and optional `paired_plant_effects.csv` to inspect condition/fault/plant cells in the browser.

## Run locally

From the repository root:

```bash
python scripts/serve_dashboard.py
```

Then open:

```text
http://127.0.0.1:8765
```

The main cockpit is the default page. Use **Phase 7 explorer** in the navigation for the local result-bundle loader.

## Browser behavior

The dashboard is dependency-free HTML, CSS, and JavaScript. Phase 7 result files are parsed locally in the browser session and are not uploaded by the cockpit.

The main cockpit can make a read-only request to the public GitHub Actions API when **Refresh status** is used so the current workflow state can be displayed. If that request is unavailable or rate-limited, the audited evidence snapshot remains usable.

## Vercel deployment

The interface can be hosted as a static Vercel project. The safest setup is to import `suhaslord/uav-safety-research` as a **new** Vercel project rather than attaching it to an unrelated existing project.

Recommended project settings:

- Framework Preset: **Other**
- Build Command: **none**
- Install Command: **none**
- Root Directory: **`dashboard`**
- Production Branch: choose the branch you intentionally want to publish; the current Phase 9 work remains a draft review branch

The cockpit's research-document links point back to the corresponding files on GitHub so they remain valid when `dashboard` is deployed as the Vercel project root.

Do not expose secrets or add backend credentials for this dashboard. The current interface needs none.

## Research boundary

AegisLand remains simulation-only research. The dashboard does not change any frozen detector, controller, confidence gate, evidence role, or scientific acceptance rule. A passing UI check or hosted dashboard is not physical-flight validation, and the Phase 9 seen trace must not be presented as a general safety verdict.
