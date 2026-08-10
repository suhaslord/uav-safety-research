from __future__ import annotations

from pathlib import Path
import argparse
import html
import json


EXPECTED_SCHEMA = "aegisland.phase7.dashboard-bundle.v1"


def _pct(value: float | int | str | None) -> str:
    try:
        return f"{100.0 * float(value):.1f}%"
    except (TypeError, ValueError):
        return "—"


def _pp(value: float | int | str | None) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"
    prefix = "+" if number > 0 else ""
    return f"{prefix}{number:.1f} pp"


def _ci(row: dict, prefix: str) -> str:
    low = row.get(f"{prefix}_ci_low")
    high = row.get(f"{prefix}_ci_high")
    if low is None or high is None:
        return "CI unavailable"
    return f"95% CI {_pct(low)}–{_pct(high)}"


def _human(value: object) -> str:
    return html.escape(str(value).replace("_", " "))


def render_report(bundle: dict, *, title: str = "AegisLand Phase 7 Development Report") -> str:
    if bundle.get("schema") != EXPECTED_SCHEMA:
        raise ValueError(f"unsupported dashboard bundle schema: {bundle.get('schema')!r}")

    metadata = bundle.get("metadata") or {}
    summary = bundle.get("summary") or []
    paired = bundle.get("paired_plant_effects") or []
    if not summary:
        raise ValueError("dashboard bundle contains no summary rows")

    weakest = sorted(
        summary,
        key=lambda row: (
            -float(row.get("unsafe_touchdown_rate", 0.0)),
            float(row.get("success_rate", 1.0)),
            str(row.get("condition", "")),
            str(row.get("fault_scenario", "")),
            str(row.get("plant_model", "")),
        ),
    )[:8]

    weakest_rows = "".join(
        "<tr>"
        f"<td>{_human(row.get('condition'))}</td>"
        f"<td>{_human(row.get('fault_scenario'))}</td>"
        f"<td>{_human(row.get('plant_model'))}</td>"
        f"<td><strong>{_pct(row.get('unsafe_touchdown_rate'))}</strong><span>{_ci(row, 'unsafe')}</span></td>"
        f"<td>{_pct(row.get('success_rate'))}</td>"
        f"<td>{html.escape(str(row.get('episodes', '—')))}</td>"
        "</tr>"
        for row in weakest
    )

    summary_rows = "".join(
        "<tr>"
        f"<td>{_human(row.get('condition'))}</td>"
        f"<td>{_human(row.get('fault_scenario'))}</td>"
        f"<td>{_human(row.get('plant_model'))}</td>"
        f"<td>{_pct(row.get('success_rate'))}</td>"
        f"<td>{_pct(row.get('unsafe_touchdown_rate'))}</td>"
        f"<td>{_pct(row.get('abort_rate'))}</td>"
        f"<td>{_pct(row.get('mean_shared_dropout_event_rate'))}</td>"
        f"<td>{_pct(row.get('mean_image_drop_rate'))}</td>"
        f"<td>{_pct(row.get('mean_reference_available_rate'))}</td>"
        f"<td>{html.escape(f\"{float(row.get('mean_reference_age_steps', 0.0)):.2f}\")}</td>"
        "</tr>"
        for row in summary
    )

    paired_rows = "".join(
        "<tr>"
        f"<td>{_human(row.get('condition'))}</td>"
        f"<td>{_human(row.get('fault_scenario'))}</td>"
        f"<td>{_pp(row.get('phase7_minus_legacy_success_pp'))}</td>"
        f"<td>{_pp(row.get('phase7_minus_legacy_unsafe_pp'))}</td>"
        f"<td>{html.escape(str(row.get('paired_episodes', '—')))}</td>"
        "</tr>"
        for row in paired
    ) or '<tr><td colspan="5">Paired plant effects unavailable.</td></tr>'

    semantics = [
        ("Camera randomness", metadata.get("image_rng_model", "unknown")),
        ("Sensor transport", metadata.get("sensor_transport_model", "unknown")),
        ("Sensor RNG", metadata.get("sensor_rng_model", "unknown")),
        ("Lateral freshness", metadata.get("reference_lateral_freshness_model", "unknown")),
        ("Component freshness", metadata.get("component_reference_freshness_model", "unknown")),
        ("Shared dropout", metadata.get("shared_dropout_model", "unknown")),
    ]
    semantic_cards = "".join(
        f'<div class="semantic"><span>{html.escape(label)}</span><strong>{_human(value)}</strong></div>'
        for label, value in semantics
    )

    git_sha = html.escape(str(metadata.get("git_sha", "unknown")))
    seed = html.escape(str(metadata.get("episode_seed", "unknown")))
    seed_status = _human(metadata.get("episode_seed_status", "unknown"))
    run_role = _human(metadata.get("run_role", "unknown"))
    per_cell = html.escape(str(metadata.get("episodes_per_condition_fault_plant", "unknown")))

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
:root {{ color-scheme: dark; font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; --bg:#080a0f; --panel:#111620; --line:#242d3d; --text:#f6f8fc; --muted:#9aa5b7; --accent:#8db3ff; --danger:#ff969d; --good:#7de2ad; }}
*{{box-sizing:border-box}} body{{margin:0;background:radial-gradient(circle at 15% 0,#15233f 0,transparent 34%),var(--bg);color:var(--text)}}
main{{width:min(1280px,calc(100% - 32px));margin:auto;padding:48px 0 72px}} .hero{{padding:38px;border:1px solid var(--line);border-radius:24px;background:linear-gradient(145deg,#151c29,#0d1119)}}
.kicker{{font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:var(--accent);font-weight:800}} h1{{font-size:clamp(36px,6vw,72px);line-height:.96;letter-spacing:-.055em;margin:10px 0 18px;max-width:900px}} p{{color:var(--muted);line-height:1.65}}
.notice{{margin-top:20px;padding:14px 16px;border-radius:14px;border:1px solid #4a3d22;background:#1f1a10;color:#ffd889;font-size:13px}} .meta{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:16px}}
.meta div,.semantic{{padding:16px;border:1px solid var(--line);border-radius:15px;background:#0d121b}} .meta span,.semantic span{{display:block;color:var(--muted);font-size:11px;margin-bottom:7px}} .meta strong,.semantic strong{{font-size:13px;word-break:break-word}}
section{{margin-top:20px;padding:26px;border:1px solid var(--line);border-radius:22px;background:rgba(17,22,32,.92)}} h2{{margin:0 0 18px;font-size:22px;letter-spacing:-.025em}} .semantics{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}}
.table-wrap{{overflow:auto}} table{{width:100%;border-collapse:collapse;min-width:800px}} th,td{{padding:12px 10px;border-bottom:1px solid var(--line);text-align:left;font-size:12px}} th{{color:var(--muted);font-size:10px;text-transform:uppercase;letter-spacing:.08em}} td strong{{color:#ffd0d3;font-size:16px}} td span{{display:block;color:var(--muted);font-size:10px;margin-top:3px}}
.footer{{margin-top:24px;color:var(--muted);font-size:12px;line-height:1.6}} @media(max-width:800px){{.meta,.semantics{{grid-template-columns:1fr 1fr}}}} @media(max-width:520px){{main{{width:min(100% - 18px,1280px);padding-top:18px}}.hero,section{{padding:20px}}.meta,.semantics{{grid-template-columns:1fr}}}}
</style>
</head>
<body><main>
<header class="hero">
<div class="kicker">AEGISLAND · PHASE 7 · EXTERNAL VALIDITY</div>
<h1>{html.escape(title)}</h1>
<p>This report renders one checksum-trackable Phase 7 dashboard bundle. It preserves the development label and keeps the frozen Phase 6B result separate.</p>
<div class="notice"><strong>Development evidence only.</strong> Small cells and a seen development seed are useful for finding failure modes, not for claiming zero real-world risk.</div>
<div class="meta">
<div><span>Run role</span><strong>{run_role}</strong></div>
<div><span>Executable commit</span><strong>{git_sha}</strong></div>
<div><span>Episode seed</span><strong>{seed} · {seed_status}</strong></div>
<div><span>Episodes / cell</span><strong>{per_cell}</strong></div>
</div>
</header>
<section><h2>Audited architecture semantics</h2><div class="semantics">{semantic_cards}</div></section>
<section><h2>Weakest observed cells</h2><div class="table-wrap"><table><thead><tr><th>Condition</th><th>Fault</th><th>Plant</th><th>Unsafe touchdown</th><th>Success</th><th>n</th></tr></thead><tbody>{weakest_rows}</tbody></table></div></section>
<section><h2>Paired plant effects</h2><div class="table-wrap"><table><thead><tr><th>Condition</th><th>Fault</th><th>Δ success</th><th>Δ unsafe</th><th>Paired n</th></tr></thead><tbody>{paired_rows}</tbody></table></div></section>
<section><h2>Complete aggregate table</h2><div class="table-wrap"><table><thead><tr><th>Condition</th><th>Fault</th><th>Plant</th><th>Success</th><th>Unsafe</th><th>Abort</th><th>Common outage</th><th>Image drop</th><th>Reference available</th><th>Mean ref age</th></tr></thead><tbody>{summary_rows}</tbody></table></div></section>
<div class="footer">Simulation-only research. The report is generated from aggregate development data and is not a vehicle-control surface or physical-flight validation.</div>
</main></body></html>"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a standalone HTML report from a Phase 7 dashboard bundle.")
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--out", type=Path, default=Path("phase7_report.html"))
    parser.add_argument("--title", default="AegisLand Phase 7 Development Report")
    args = parser.parse_args()

    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    args.out.write_text(render_report(bundle, title=args.title), encoding="utf-8")
    print(f"Rendered {args.out.resolve()}")


if __name__ == "__main__":
    main()
