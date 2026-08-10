from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import html
import json
import math

import numpy as np
import pandas as pd

from .external_trace import load_external_trace, validate_external_trace
from .provenance import sha256_file, write_result_manifest


PHASE8_TRACE_COMPARISON_SCHEMA = "aegisland.phase8.trace-comparison.v1"
PHASE8_RESULT_MANIFEST_SCHEMA = "aegisland.phase8.result-bundle.v1"
PHASE7_AUDITED_BASELINE_COMMIT = "7354eeda8b975f45b659ce4f3f86c82501e6321d"
PHASE6B_FROZEN_COMMIT = "b4e9838555e935a5ec42690495315473629b58f6"

EXTERNAL_EVIDENCE_STATUSES = (
    "fixture_non_authoritative",
    "external_simulator_seen",
    "external_simulator_unseen",
)

FEATURE_SCALE_FLOORS = {
    "dt_s": 0.01,
    "image_x_error_m": 0.05,
    "image_z_error_m": 0.05,
    "image_vx_error_mps": 0.05,
    "image_vz_error_mps": 0.05,
    "reference_x_error_m": 0.05,
    "reference_z_error_m": 0.05,
    "reference_vx_error_mps": 0.05,
    "reference_vz_error_mps": 0.05,
    "image_confidence": 0.05,
    "image_sigma_pos_m": 0.05,
    "reference_sigma_pos_m": 0.05,
    "reference_fresh_interval_s": 0.02,
    "image_drop_run_frames": 1.0,
    "reference_unavailable_run_frames": 1.0,
    "image_transport_latency_s": 0.01,
    "reference_transport_latency_s": 0.01,
    "reference_state_age_s": 0.01,
}


@dataclass(frozen=True)
class Phase8ComparisonThresholds:
    """Predeclared descriptive thresholds for trace-resemblance diagnostics.

    These thresholds classify modeling discrepancies only. They are not flight
    safety thresholds and must not be used to tune Phase 6B or Phase 7 gates.
    """

    min_samples: int = 20
    ks_close: float = 0.15
    ks_mismatch: float = 0.30
    normalized_w1_close: float = 0.25
    normalized_w1_mismatch: float = 0.50
    rate_delta_close: float = 0.05
    rate_delta_mismatch: float = 0.15
    correlation_delta_close: float = 0.10
    correlation_delta_mismatch: float = 0.30


DEFAULT_PHASE8_THRESHOLDS = Phase8ComparisonThresholds()


def _safe_number(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _json_safe(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return _safe_number(value)
    return value


def _finite(values: np.ndarray | pd.Series | list[float]) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    return array[np.isfinite(array)]


def _safe_correlation(a: np.ndarray, b: np.ndarray) -> float | None:
    a = _finite(a)
    b = _finite(b)
    if len(a) != len(b) or len(a) < 3:
        return None
    if float(np.std(a)) < 1e-12 or float(np.std(b)) < 1e-12:
        return None
    value = float(np.corrcoef(a, b)[0, 1])
    return value if math.isfinite(value) else None


def _lag1(values: np.ndarray) -> float | None:
    values = _finite(values)
    if len(values) < 4:
        return None
    return _safe_correlation(values[:-1], values[1:])


def _run_lengths(mask: np.ndarray) -> np.ndarray:
    mask = np.asarray(mask, dtype=bool)
    lengths: list[int] = []
    current = 0
    for active in mask:
        if active:
            current += 1
        elif current:
            lengths.append(current)
            current = 0
    if current:
        lengths.append(current)
    return np.asarray(lengths, dtype=float)


def _empirical_ks(a: np.ndarray, b: np.ndarray) -> float | None:
    a = np.sort(_finite(a))
    b = np.sort(_finite(b))
    if not len(a) or not len(b):
        return None
    points = np.sort(np.concatenate([a, b]))
    cdf_a = np.searchsorted(a, points, side="right") / len(a)
    cdf_b = np.searchsorted(b, points, side="right") / len(b)
    return float(np.max(np.abs(cdf_a - cdf_b)))


def _quantile_w1(a: np.ndarray, b: np.ndarray) -> float | None:
    a = _finite(a)
    b = _finite(b)
    if not len(a) or not len(b):
        return None
    quantiles = np.linspace(0.0, 1.0, 201)
    return float(np.mean(np.abs(np.quantile(a, quantiles) - np.quantile(b, quantiles))))


def _scale(values: np.ndarray, *, floor: float) -> float:
    values = _finite(values)
    if not len(values):
        return float(floor)
    q25, q75 = np.quantile(values, [0.25, 0.75])
    iqr = float(q75 - q25)
    std = float(np.std(values))
    return max(float(floor), iqr, std)


def _summary_stats(values: np.ndarray) -> dict:
    values = _finite(values)
    if not len(values):
        return {
            "n": 0,
            "mean": None,
            "std": None,
            "q05": None,
            "q50": None,
            "q95": None,
        }
    q05, q50, q95 = np.quantile(values, [0.05, 0.50, 0.95])
    return {
        "n": int(len(values)),
        "mean": float(np.mean(values)),
        "std": float(np.std(values)),
        "q05": float(q05),
        "q50": float(q50),
        "q95": float(q95),
    }


def _error_series(frame: pd.DataFrame, source: str, field: str, truth_field: str) -> np.ndarray:
    if source == "image":
        mask = ~frame["image_dropped"].to_numpy(dtype=bool)
    elif source == "reference":
        mask = frame["reference_available"].to_numpy(dtype=bool)
    else:
        raise ValueError(source)
    return (
        frame.loc[mask, field].to_numpy(dtype=float)
        - frame.loc[mask, truth_field].to_numpy(dtype=float)
    )


def _paired_errors(frame: pd.DataFrame, *, axis: str) -> tuple[np.ndarray, np.ndarray]:
    mask = (~frame["image_dropped"]) & frame["reference_available"]
    truth = frame.loc[mask, f"truth_{axis}_m"].to_numpy(dtype=float)
    image = frame.loc[mask, f"image_{axis}_m"].to_numpy(dtype=float) - truth
    reference = frame.loc[mask, f"reference_{axis}_m"].to_numpy(dtype=float) - truth
    return image, reference


def extract_trace_feature_series(frame: pd.DataFrame) -> dict[str, np.ndarray]:
    """Extract comparable empirical series without resampling either trace."""

    normalized, _ = validate_external_trace(frame)
    t = normalized["t_s"].to_numpy(dtype=float)
    fresh_times = normalized.loc[normalized["reference_fresh"], "t_s"].to_numpy(dtype=float)

    series: dict[str, np.ndarray] = {
        "dt_s": np.diff(t),
        "image_x_error_m": _error_series(normalized, "image", "image_x_m", "truth_x_m"),
        "image_z_error_m": _error_series(normalized, "image", "image_z_m", "truth_z_m"),
        "image_vx_error_mps": _error_series(normalized, "image", "image_vx_mps", "truth_vx_mps"),
        "image_vz_error_mps": _error_series(normalized, "image", "image_vz_mps", "truth_vz_mps"),
        "reference_x_error_m": _error_series(normalized, "reference", "reference_x_m", "truth_x_m"),
        "reference_z_error_m": _error_series(normalized, "reference", "reference_z_m", "truth_z_m"),
        "reference_vx_error_mps": _error_series(
            normalized, "reference", "reference_vx_mps", "truth_vx_mps"
        ),
        "reference_vz_error_mps": _error_series(
            normalized, "reference", "reference_vz_mps", "truth_vz_mps"
        ),
        "image_confidence": normalized.loc[~normalized["image_dropped"], "image_confidence"].to_numpy(
            dtype=float
        ),
        "image_sigma_pos_m": normalized.loc[~normalized["image_dropped"], "image_sigma_pos_m"].to_numpy(
            dtype=float
        ),
        "reference_sigma_pos_m": normalized.loc[
            normalized["reference_available"], "reference_sigma_pos_m"
        ].to_numpy(dtype=float),
        "reference_fresh_interval_s": np.diff(fresh_times),
        "image_drop_run_frames": _run_lengths(normalized["image_dropped"].to_numpy(dtype=bool)),
        "reference_unavailable_run_frames": _run_lengths(
            ~normalized["reference_available"].to_numpy(dtype=bool)
        ),
    }

    if "image_transport_latency_s" in normalized.columns:
        series["image_transport_latency_s"] = normalized.loc[
            ~normalized["image_dropped"], "image_transport_latency_s"
        ].to_numpy(dtype=float)
    if "reference_transport_latency_s" in normalized.columns:
        series["reference_transport_latency_s"] = normalized.loc[
            normalized["reference_available"], "reference_transport_latency_s"
        ].to_numpy(dtype=float)
    if "reference_state_age_s" in normalized.columns:
        series["reference_state_age_s"] = normalized.loc[
            normalized["reference_available"], "reference_state_age_s"
        ].to_numpy(dtype=float)

    return series


def _classify_distribution(
    *,
    n_surrogate: int,
    n_external: int,
    ks: float | None,
    normalized_w1: float | None,
    thresholds: Phase8ComparisonThresholds,
) -> str:
    if n_surrogate < thresholds.min_samples or n_external < thresholds.min_samples:
        return "insufficient"
    if ks is None or normalized_w1 is None:
        return "insufficient"
    if ks >= thresholds.ks_mismatch or normalized_w1 >= thresholds.normalized_w1_mismatch:
        return "mismatch"
    if ks <= thresholds.ks_close and normalized_w1 <= thresholds.normalized_w1_close:
        return "close"
    return "watch"


def _distribution_metric(
    name: str,
    surrogate_values: np.ndarray,
    external_values: np.ndarray,
    thresholds: Phase8ComparisonThresholds,
) -> dict:
    surrogate_stats = _summary_stats(surrogate_values)
    external_stats = _summary_stats(external_values)
    ks = _empirical_ks(surrogate_values, external_values)
    w1 = _quantile_w1(surrogate_values, external_values)
    scale = _scale(external_values, floor=FEATURE_SCALE_FLOORS.get(name, 1e-3))
    normalized_w1 = None if w1 is None else float(w1 / scale)
    status = _classify_distribution(
        n_surrogate=surrogate_stats["n"],
        n_external=external_stats["n"],
        ks=ks,
        normalized_w1=normalized_w1,
        thresholds=thresholds,
    )
    return {
        "family": "distribution",
        "metric": name,
        "status": status,
        "surrogate": surrogate_stats,
        "external": external_stats,
        "ks": ks,
        "wasserstein_1": w1,
        "external_scale": scale,
        "normalized_wasserstein_1": normalized_w1,
    }


def _classify_delta(
    delta: float | None,
    *,
    close: float,
    mismatch: float,
) -> str:
    if delta is None:
        return "insufficient"
    delta = abs(float(delta))
    if delta >= mismatch:
        return "mismatch"
    if delta <= close:
        return "close"
    return "watch"


def _scalar_metric(
    name: str,
    surrogate_value: float | None,
    external_value: float | None,
    *,
    close: float,
    mismatch: float,
) -> dict:
    if surrogate_value is None or external_value is None:
        delta = None
    else:
        delta = float(surrogate_value - external_value)
    return {
        "family": "scalar",
        "metric": name,
        "status": _classify_delta(delta, close=close, mismatch=mismatch),
        "surrogate_value": surrogate_value,
        "external_value": external_value,
        "delta": delta,
    }


def _scalar_features(frame: pd.DataFrame) -> dict[str, float | None]:
    normalized, _ = validate_external_trace(frame)
    image_x = _error_series(normalized, "image", "image_x_m", "truth_x_m")
    reference_x = _error_series(normalized, "reference", "reference_x_m", "truth_x_m")
    image_z = _error_series(normalized, "image", "image_z_m", "truth_z_m")
    reference_z = _error_series(normalized, "reference", "reference_z_m", "truth_z_m")
    paired_image_x, paired_reference_x = _paired_errors(normalized, axis="x")
    paired_image_z, paired_reference_z = _paired_errors(normalized, axis="z")
    return {
        "image_drop_rate": float(normalized["image_dropped"].mean()),
        "reference_available_rate": float(normalized["reference_available"].mean()),
        "reference_fresh_rate": float(normalized["reference_fresh"].mean()),
        "lateral_error_correlation": _safe_correlation(paired_image_x, paired_reference_x),
        "vertical_error_correlation": _safe_correlation(paired_image_z, paired_reference_z),
        "image_x_error_lag1": _lag1(image_x),
        "reference_x_error_lag1": _lag1(reference_x),
        "image_z_error_lag1": _lag1(image_z),
        "reference_z_error_lag1": _lag1(reference_z),
    }


def compare_external_traces(
    surrogate: pd.DataFrame,
    external: pd.DataFrame,
    *,
    external_evidence_status: str = "fixture_non_authoritative",
    surrogate_source: str = "phase7_surrogate",
    external_source: str = "synthetic_interface_fixture",
    thresholds: Phase8ComparisonThresholds = DEFAULT_PHASE8_THRESHOLDS,
) -> dict:
    """Compare a Phase 7 surrogate trace with an independently sourced trace.

    The returned verdict concerns model resemblance only. It is deliberately not
    an autonomy/safety acceptance result and does not feed controller tuning.
    """

    if external_evidence_status not in EXTERNAL_EVIDENCE_STATUSES:
        raise ValueError(
            f"unknown external_evidence_status {external_evidence_status!r}; "
            f"expected one of {EXTERNAL_EVIDENCE_STATUSES}"
        )

    surrogate_normalized, surrogate_validation = validate_external_trace(surrogate)
    external_normalized, external_validation = validate_external_trace(external)

    surrogate_series = extract_trace_feature_series(surrogate_normalized)
    external_series = extract_trace_feature_series(external_normalized)
    feature_names = sorted(set(surrogate_series) | set(external_series))

    metrics: list[dict] = []
    for name in feature_names:
        metrics.append(
            _distribution_metric(
                name,
                surrogate_series.get(name, np.asarray([], dtype=float)),
                external_series.get(name, np.asarray([], dtype=float)),
                thresholds,
            )
        )

    surrogate_scalars = _scalar_features(surrogate_normalized)
    external_scalars = _scalar_features(external_normalized)
    rate_names = ("image_drop_rate", "reference_available_rate", "reference_fresh_rate")
    correlation_names = (
        "lateral_error_correlation",
        "vertical_error_correlation",
        "image_x_error_lag1",
        "reference_x_error_lag1",
        "image_z_error_lag1",
        "reference_z_error_lag1",
    )
    for name in rate_names:
        metrics.append(
            _scalar_metric(
                name,
                surrogate_scalars[name],
                external_scalars[name],
                close=thresholds.rate_delta_close,
                mismatch=thresholds.rate_delta_mismatch,
            )
        )
    for name in correlation_names:
        metrics.append(
            _scalar_metric(
                name,
                surrogate_scalars[name],
                external_scalars[name],
                close=thresholds.correlation_delta_close,
                mismatch=thresholds.correlation_delta_mismatch,
            )
        )

    counts = {status: sum(metric["status"] == status for metric in metrics) for status in (
        "close",
        "watch",
        "mismatch",
        "insufficient",
    )}
    if counts["mismatch"]:
        diagnostic = "diagnostic_mismatch"
    elif counts["watch"] or counts["insufficient"]:
        diagnostic = "diagnostic_watch"
    else:
        diagnostic = "diagnostic_close"

    claim_level = (
        "pipeline_validation_only"
        if external_evidence_status == "fixture_non_authoritative"
        else "external_model_resemblance_diagnostic"
    )

    return _json_safe({
        "schema": PHASE8_TRACE_COMPARISON_SCHEMA,
        "phase": 8,
        "purpose": "higher_fidelity_trace_resemblance_validation",
        "claim_level": claim_level,
        "safety_acceptance": False,
        "controller_tuning_allowed": False,
        "phase7_audited_baseline_commit": PHASE7_AUDITED_BASELINE_COMMIT,
        "historical_phase6b_frozen_commit": PHASE6B_FROZEN_COMMIT,
        "external_evidence_status": external_evidence_status,
        "surrogate_source": surrogate_source,
        "external_source": external_source,
        "thresholds": asdict(thresholds),
        "threshold_policy": "predeclared_descriptive_model_resemblance_only",
        "surrogate_validation": surrogate_validation.to_dict(),
        "external_validation": external_validation.to_dict(),
        "overall_diagnostic": diagnostic,
        "status_counts": counts,
        "metrics": metrics,
    })


def _metric_rows(bundle: dict) -> list[dict]:
    rows: list[dict] = []
    for metric in bundle.get("metrics", []):
        if metric.get("family") == "distribution":
            rows.append({
                "family": "distribution",
                "metric": metric.get("metric"),
                "status": metric.get("status"),
                "surrogate_n": metric.get("surrogate", {}).get("n"),
                "external_n": metric.get("external", {}).get("n"),
                "surrogate_mean": metric.get("surrogate", {}).get("mean"),
                "external_mean": metric.get("external", {}).get("mean"),
                "ks": metric.get("ks"),
                "wasserstein_1": metric.get("wasserstein_1"),
                "normalized_wasserstein_1": metric.get("normalized_wasserstein_1"),
                "delta": None,
            })
        else:
            rows.append({
                "family": "scalar",
                "metric": metric.get("metric"),
                "status": metric.get("status"),
                "surrogate_n": None,
                "external_n": None,
                "surrogate_mean": metric.get("surrogate_value"),
                "external_mean": metric.get("external_value"),
                "ks": None,
                "wasserstein_1": None,
                "normalized_wasserstein_1": None,
                "delta": metric.get("delta"),
            })
    return rows


def render_phase8_summary(bundle: dict) -> str:
    counts = bundle["status_counts"]
    fixture_warning = ""
    if bundle["external_evidence_status"] == "fixture_non_authoritative":
        fixture_warning = (
            "\n> **NON-AUTHORITATIVE FIXTURE:** this run validates the Phase 8 analysis pipeline only. "
            "It is not higher-fidelity external-simulator evidence.\n"
        )
    return (
        "# AegisLand Phase 8 trace comparison\n\n"
        f"- Overall diagnostic: `{bundle['overall_diagnostic']}`\n"
        f"- Claim level: `{bundle['claim_level']}`\n"
        f"- External evidence status: `{bundle['external_evidence_status']}`\n"
        f"- Phase 7 audited baseline: `{bundle['phase7_audited_baseline_commit']}`\n"
        f"- Frozen Phase 6B: `{bundle['historical_phase6b_frozen_commit']}`\n"
        f"- Close / watch / mismatch / insufficient: "
        f"{counts['close']} / {counts['watch']} / {counts['mismatch']} / {counts['insufficient']}\n"
        "- Safety acceptance: `false`\n"
        "- Controller tuning from this comparison: `false`\n"
        f"{fixture_warning}\n"
        "The diagnostic describes empirical resemblance between two traces. A mismatch is a model limitation "
        "to investigate, not permission to retune the frozen Phase 6B gates against the observed trace.\n"
    )


def _fmt(value: object, digits: int = 3) -> str:
    number = _safe_number(value)
    return "—" if number is None else f"{number:.{digits}f}"


def render_phase8_report(bundle: dict, *, title: str = "AegisLand Phase 8 Trace Validation") -> str:
    if bundle.get("schema") != PHASE8_TRACE_COMPARISON_SCHEMA:
        raise ValueError(f"unsupported Phase 8 bundle schema: {bundle.get('schema')!r}")

    rank = {"mismatch": 0, "watch": 1, "insufficient": 2, "close": 3}
    metrics = sorted(bundle.get("metrics", []), key=lambda row: (rank.get(row.get("status"), 9), row.get("metric", "")))
    rows: list[str] = []
    for metric in metrics:
        if metric.get("family") == "distribution":
            surrogate_value = metric.get("surrogate", {}).get("mean")
            external_value = metric.get("external", {}).get("mean")
            detail = f"KS {_fmt(metric.get('ks'))} · nW1 {_fmt(metric.get('normalized_wasserstein_1'))}"
        else:
            surrogate_value = metric.get("surrogate_value")
            external_value = metric.get("external_value")
            detail = f"Δ {_fmt(metric.get('delta'))}"
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(metric.get('metric', 'unknown')).replace('_', ' '))}</td>"
            f"<td><span class=\"badge {html.escape(str(metric.get('status', 'unknown')))}\">{html.escape(str(metric.get('status', 'unknown')))}</span></td>"
            f"<td>{_fmt(surrogate_value)}</td>"
            f"<td>{_fmt(external_value)}</td>"
            f"<td>{html.escape(detail)}</td>"
            "</tr>"
        )

    fixture_notice = (
        "This bundle uses a NON-AUTHORITATIVE interface fixture. It proves the comparison pipeline, not external validity."
        if bundle.get("external_evidence_status") == "fixture_non_authoritative"
        else "This bundle is labeled external-simulator evidence; interpret the metrics as model-resemblance diagnostics only."
    )
    counts = bundle.get("status_counts", {})
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<style>
:root{{font-family:Inter,ui-sans-serif,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color-scheme:dark;--bg:#080a0e;--panel:#111722;--line:#273043;--text:#f7f9fd;--muted:#9ca8bb;--close:#74d69d;--watch:#ffd37a;--mismatch:#ff8f98;--insufficient:#aeb8c8}}
*{{box-sizing:border-box}}body{{margin:0;background:radial-gradient(circle at 20% 0,#182849,transparent 32%),var(--bg);color:var(--text)}}main{{width:min(1200px,calc(100% - 28px));margin:auto;padding:38px 0 70px}}header,section{{background:rgba(17,23,34,.94);border:1px solid var(--line);border-radius:22px;padding:26px;margin-bottom:16px}}.kicker{{font-size:11px;font-weight:800;letter-spacing:.16em;color:#8db3ff}}h1{{font-size:clamp(36px,6vw,68px);line-height:1;letter-spacing:-.05em;margin:10px 0 14px}}p{{color:var(--muted);line-height:1.6}}.notice{{border:1px solid #4a3d22;background:#201a10;color:#ffda8b;padding:14px;border-radius:14px}}.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:16px}}.card{{border:1px solid var(--line);border-radius:14px;padding:15px;background:#0d121b}}.card span{{display:block;font-size:10px;color:var(--muted);margin-bottom:6px}}.card strong{{font-size:16px}}.table-wrap{{overflow:auto}}table{{border-collapse:collapse;width:100%;min-width:760px}}th,td{{padding:11px 9px;border-bottom:1px solid var(--line);text-align:left;font-size:12px}}th{{font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}}.badge{{display:inline-block;padding:4px 8px;border-radius:999px;font-size:10px;font-weight:800;text-transform:uppercase}}.badge.close{{color:var(--close);background:#10251a}}.badge.watch{{color:var(--watch);background:#2b2312}}.badge.mismatch{{color:var(--mismatch);background:#2a1519}}.badge.insufficient{{color:var(--insufficient);background:#1c222c}}code{{word-break:break-all}}@media(max-width:760px){{.grid{{grid-template-columns:1fr 1fr}}}}@media(max-width:480px){{.grid{{grid-template-columns:1fr}}header,section{{padding:19px}}}}
</style></head><body><main>
<header><div class="kicker">AEGISLAND · PHASE 8 · TRACE VALIDATION</div><h1>{html.escape(title)}</h1>
<p>Independent trace comparison for model resemblance. This surface does not expose controller tuning controls and does not produce a flight-safety pass/fail.</p>
<div class="notice"><strong>Evidence label:</strong> {html.escape(fixture_notice)}</div>
<div class="grid">
<div class="card"><span>Diagnostic</span><strong>{html.escape(str(bundle.get('overall_diagnostic')))}</strong></div>
<div class="card"><span>Close</span><strong>{counts.get('close', 0)}</strong></div>
<div class="card"><span>Mismatch</span><strong>{counts.get('mismatch', 0)}</strong></div>
<div class="card"><span>Insufficient</span><strong>{counts.get('insufficient', 0)}</strong></div>
</div></header>
<section><h2>Provenance</h2><p>Phase 7 baseline <code>{html.escape(str(bundle.get('phase7_audited_baseline_commit')))}</code><br>Frozen Phase 6B <code>{html.escape(str(bundle.get('historical_phase6b_frozen_commit')))}</code><br>External source {html.escape(str(bundle.get('external_source')))} · status {html.escape(str(bundle.get('external_evidence_status')))}</p></section>
<section><h2>Resemblance metrics</h2><div class="table-wrap"><table><thead><tr><th>Metric</th><th>Status</th><th>Phase 7 surrogate</th><th>External</th><th>Distance / delta</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div></section>
<section><h2>Interpretation boundary</h2><p>A mismatch should be documented and investigated. The Phase 6B frozen gates and the audited Phase 7 baseline are not retuned against these observed traces. Physical flight is outside this phase.</p></section>
</main></body></html>"""


def write_phase8_comparison(
    surrogate_path: str | Path,
    external_path: str | Path,
    out_dir: str | Path,
    *,
    git_sha: str,
    external_evidence_status: str = "fixture_non_authoritative",
    surrogate_source: str = "phase7_surrogate",
    external_source: str = "synthetic_interface_fixture",
    thresholds: Phase8ComparisonThresholds = DEFAULT_PHASE8_THRESHOLDS,
) -> dict:
    """Run the complete offline Phase 8 comparison and write a hashed bundle."""

    surrogate_path = Path(surrogate_path)
    external_path = Path(external_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    surrogate, surrogate_validation = load_external_trace(surrogate_path)
    external, external_validation = load_external_trace(external_path)
    bundle = compare_external_traces(
        surrogate,
        external,
        external_evidence_status=external_evidence_status,
        surrogate_source=surrogate_source,
        external_source=external_source,
        thresholds=thresholds,
    )
    bundle["git_sha"] = git_sha
    bundle["input_provenance"] = {
        "surrogate": {
            "filename": surrogate_path.name,
            "bytes": surrogate_path.stat().st_size,
            "sha256": sha256_file(surrogate_path),
            "validation": _json_safe(surrogate_validation.to_dict()),
        },
        "external": {
            "filename": external_path.name,
            "bytes": external_path.stat().st_size,
            "sha256": sha256_file(external_path),
            "validation": _json_safe(external_validation.to_dict()),
        },
    }

    bundle_path = out_dir / "trace_comparison.json"
    bundle_path.write_text(json.dumps(_json_safe(bundle), indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")

    metrics_path = out_dir / "metric_comparison.csv"
    pd.DataFrame(_metric_rows(bundle)).to_csv(metrics_path, index=False)

    summary_path = out_dir / "summary.md"
    summary_path.write_text(render_phase8_summary(bundle), encoding="utf-8")

    report_path = out_dir / "phase8_report.html"
    report_path.write_text(render_phase8_report(bundle), encoding="utf-8")

    metadata = {
        "schema": "aegisland.phase8.run-metadata.v1",
        "git_sha": git_sha,
        "phase7_audited_baseline_commit": PHASE7_AUDITED_BASELINE_COMMIT,
        "historical_phase6b_frozen_commit": PHASE6B_FROZEN_COMMIT,
        "external_evidence_status": external_evidence_status,
        "surrogate_source": surrogate_source,
        "external_source": external_source,
        "controller_tuning_allowed": False,
        "safety_acceptance": False,
        "thresholds": asdict(thresholds),
        "input_provenance": bundle["input_provenance"],
    }
    metadata_path = out_dir / "run_metadata.json"
    metadata_path.write_text(json.dumps(_json_safe(metadata), indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")

    filenames = [
        bundle_path.name,
        metrics_path.name,
        summary_path.name,
        report_path.name,
        metadata_path.name,
    ]
    manifest_path = write_result_manifest(
        out_dir,
        filenames,
        schema=PHASE8_RESULT_MANIFEST_SCHEMA,
        extra={
            "git_sha": git_sha,
            "phase7_audited_baseline_commit": PHASE7_AUDITED_BASELINE_COMMIT,
            "historical_phase6b_frozen_commit": PHASE6B_FROZEN_COMMIT,
            "external_evidence_status": external_evidence_status,
            "safety_acceptance": False,
            "controller_tuning_allowed": False,
        },
    )

    return {
        "bundle": bundle,
        "bundle_path": bundle_path,
        "metrics_path": metrics_path,
        "summary_path": summary_path,
        "report_path": report_path,
        "metadata_path": metadata_path,
        "manifest_path": manifest_path,
    }
