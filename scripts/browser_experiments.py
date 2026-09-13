"""Bounded exploratory experiments, never the sealed research evaluations."""
from dataclasses import asdict, replace
import json
import math
import numpy as np
import phase_math as pm

PHASES = ['phase1', 'phase2', 'phase3', 'phase4', 'phase5', 'phase6', 'phase6b', 'phase7', 'phase8', 'phase9', 'phase10', 'phase10r', 'phase11', 'phase12', 'phase13a', 'phase13b', 'phase13c', 'phase14', 'phase15', 'phase16', 'phase17', 'phase18', 'phase19', 'phase20', 'phase21', 'phase22']
FIELDS = {
    'seed': (0, 2147483647, 2026), 'samples': (32, 1024, 128),
    'episodes': (1, 10, 3), 'offset': (-3, 3, 1.5), 'altitude': (1, 10, 6),
    'noise': (0.01, 2, 0.15), 'bias': (-2, 2, 0.3), 'dropout': (0, .8, .1),
    'severity': (.1, 3, 1), 'lag': (0, 12, 2), 'tau': (.05, 2, .24),
    'coefficient': (-.95, .95, .65), 'alternative': (-.95, .95, .85),
    'coverage': (.6, .99, .95), 'shift': (1, 5, 2), 'radius': (.1, 5, 1),
    'interaction': (0, .3, .04), 'edge': (0, .2, .04), 'oblique': (0, .2, .03),
    'dim': (0, .2, .025), 'blur_noise': (0, .2, .035), 'low_contrast': (0, .2, .02),
}
INTEGERS = {'seed', 'samples', 'episodes', 'lag'}

def validated(raw):
    if not isinstance(raw, dict) or raw.get('phase') not in PHASES:
        raise ValueError('Choose a phase from the experiment list.')
    out = {'phase': raw['phase']}
    for key, (lo, hi, default) in FIELDS.items():
        value = raw.get(key, default)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not lo <= value <= hi:
            raise ValueError(f'{key} must be between {lo} and {hi}.')
        if key in INTEGERS and value != int(value):
            raise ValueError(f'{key} must be a whole number.')
        out[key] = int(value) if key in INTEGERS else float(value)
    condition = raw.get('condition', 'mixed')
    if condition not in ('clean', 'blur', 'low_light', 'occlusion', 'mixed'):
        raise ValueError('Choose a supported camera condition.')
    out['condition'] = condition
    return out

def metric(label, value, unit=''):
    return {'label': label, 'value': float(value) if value is not None else None, 'unit': unit}

def series(label, values):
    return {'label': label, 'values': [float(x) if np.isfinite(x) else None for x in values]}

def output(title, metrics, rows, lines=None, note='', x_label='Sample', y_label='Error (m)'):
    return {'title': title, 'metrics': metrics, 'rows': rows, 'series': lines or [], 'note': note, 'x_label': x_label, 'y_label': y_label}

def landing(p, progress):
    from uav_safety.config import SimConfig
    from uav_safety.perception import PROFILES
    from uav_safety.simulator import run_episode
    from uav_safety.simulator_v2 import run_episode_v2
    from uav_safety.simulator_v3 import run_episode_v3
    cfg = SimConfig(initial_x_range=(p['offset'], p['offset']), initial_z_range=(p['altitude'], p['altitude']))
    profile = replace(PROFILES[p['condition']], dropout_prob=p['dropout'], bias_x=p['bias'], sigma_x=p['noise'])
    version = {'phase1': 1, 'phase2': 2, 'phase3': 3, 'phase5': 3}[p['phase']]
    rows, traces = [], []
    for i in range(p['episodes']):
        seed = p['seed'] + i
        base, bt = run_episode(seed, p['condition'], False, sim_cfg=cfg, perception_profile=profile, return_trace=True)
        if version == 1:
            result, rt = run_episode(seed, p['condition'], True, sim_cfg=cfg, perception_profile=profile, return_trace=True)
        else:
            fn = run_episode_v2 if version == 2 else run_episode_v3
            result, rt = fn(seed, p['condition'], sim_cfg=cfg, perception_profile=profile, return_trace=True)
        rows.append({'Seed': seed, 'Baseline outcome': base.outcome, 'Aegis outcome': result.outcome, 'Final lateral error (m)': result.final_x_error, 'Interventions': result.interventions})
        traces.append((base, result))
        progress(i + 1, p['episodes'])
    metrics = [metric('Aegis successful landings', sum(r.success for _, r in traces) / len(traces) * 100, '%'), metric('Baseline unsafe touchdowns', sum(b.unsafe_touchdown for b, _ in traces)), metric('Aegis unsafe touchdowns', sum(r.unsafe_touchdown for _, r in traces))]
    return output(f'Baseline vs Aegis V{version}', metrics, rows, [series('Baseline lateral position', [x['x'] for x in bt]), series('Aegis lateral position', [x['x'] for x in rt])], 'Original landing simulators, paired by seed. The chart shows the last episode. Small exploratory batches do not establish safety.', 'Step (0.05 s)', 'Lateral position (m)')

def camera(p, progress):
    from uav_safety.image_temporal import Phase6LandingPadRenderer, Phase6PadEstimator
    from uav_safety.selective_confidence_v2 import SharpnessAwarePadEstimator, altitude_observability_cap
    rng = np.random.default_rng(p['seed'])
    renderer = Phase6LandingPadRenderer()
    estimator = SharpnessAwarePadEstimator() if p['phase'] == 'phase6b' else Phase6PadEstimator()
    rows, errors, confidences = [], [], []
    for i in range(min(p['samples'], 128)):
        frame = renderer.render(p['offset'], p['altitude'], rng, p['condition'], p['severity'])
        m = estimator.estimate(frame)
        err = m.x_m - p['offset'] if m.valid else None
        rows.append({'Frame': i, 'Available': m.valid, 'Lateral error (m)': err, 'Altitude estimate (m)': m.z_m if m.valid else None, 'Confidence': m.raw_confidence, **({'Altitude confidence cap': altitude_observability_cap(m)} if p['phase'] == 'phase6b' else {})})
        errors.append(np.nan if err is None else err)
        confidences.append(m.raw_confidence)
    finite = np.asarray(errors)[np.isfinite(errors)]
    result = output('Synthetic camera measurement test', [metric('Available frames', len(finite) / len(rows) * 100, '%'), metric('Mean confidence', np.mean(confidences)), metric('Lateral RMSE', np.sqrt(np.mean(finite ** 2)) if len(finite) else None, 'm')], rows, [series('Lateral measurement error', errors)], 'Runs the original Phase 6 renderer and estimator; Phase 6B adds its original sharpness and altitude-observability methods. This tests perception components, not the full landing loop.', 'Frame')
    result['image'] = (np.clip(frame, 0, 1) * 255).astype(int).tolist()
    return result

def dynamics(p, progress):
    from uav_safety.config import SimConfig
    from uav_safety.dynamics import State, step_dynamics
    from uav_safety.dynamics_phase7 import Phase7DynamicsConfig, Phase7PlantMemory, step_phase7_dynamics
    cfg = SimConfig()
    dyn = Phase7DynamicsConfig(actuator_time_constant_s=p['tau'])
    state = State(x=0., z=p['altitude'], vx=0., vz=0.)
    reference = state
    memory = Phase7PlantMemory()
    rng = np.random.default_rng(p['seed'])
    rows = []
    for i in range(p['samples']):
        command = np.sin(i * .05) * p['severity']
        reference = step_dynamics(reference, command, 0, 0, 0, cfg)
        state, memory = step_phase7_dynamics(state, memory, command, 0, 0, 0, rng, cfg, dyn)
        rows.append({'Step': i, 'Point-mass x (m)': reference.x, 'Lagged-plant x (m)': state.x, 'Actual acceleration': memory.actual_ax})
    errors = np.array([r['Lagged-plant x (m)'] - r['Point-mass x (m)'] for r in rows])
    return output('Actuator lag and plant mismatch', [metric('Position mismatch RMSE', np.sqrt(np.mean(errors ** 2)), 'm'), metric('Actuator time constant', p['tau'], 's'), metric('Simulated duration', p['samples'] * .05, 's')], rows, [series('Point-mass plant', [r['Point-mass x (m)'] for r in rows]), series('Phase 7 plant', [r['Lagged-plant x (m)'] for r in rows])], 'Original point-mass and Phase 7 plant dynamics under the same sinusoidal command. The nonlinear plant includes its original colored disturbance.', 'Step (0.05 s)', 'Lateral position (m)')

def temporal(p, progress):
    from uav_safety.phase10_metric import MetricFrame, run_sequence
    rng = np.random.default_rng(p['seed'])
    t = np.arange(p['samples']) * .1
    truth = p['offset'] * np.sin(t * .7)
    raw = truth + rng.normal(0, p['noise'], len(t))
    if p['phase'] == 'phase10r':
        raw += p['bias'] + rng.normal(0, p['noise'] * (p['shift'] - 1), len(t))
    available = rng.random(len(t)) >= p['dropout']
    available[0] = True
    frames = [MetricFrame(float(t[i]), i, bool(available[i]), float(raw[i]) if available[i] else None, p['altitude'] if available[i] else None, 'aruco' if i % 5 == 0 else 'quad_fallback', .5, 1400.) for i in range(len(t))]
    estimates = run_sequence(frames)
    filtered = np.array([e.lateral_x_m if e.metric_estimate_available else np.nan for e in estimates])
    valid = np.isfinite(filtered)
    rows = [{'Frame': i, 'Truth (m)': truth[i], 'Observation (m)': raw[i] if available[i] else None, 'Estimate (m)': filtered[i] if valid[i] else None, 'Source': estimates[i].source} for i in range(len(t))]
    return output('Temporal metric estimator', [metric('Estimator availability', np.mean(valid) * 100, '%'), metric('Estimator RMSE', np.sqrt(np.mean((filtered[valid] - truth[valid]) ** 2)), 'm'), metric('Fresh geometry updates', sum(e.fresh_geometry_update for e in estimates))], rows, [series('Truth', truth), series('AegisT10 estimate', filtered)], 'Original AegisT10 estimator on a newly generated synthetic measurement sequence. Phase 10R adds custom distribution shift; this is not a rerun of its sealed holdout.', 'Frame (0.1 s)', 'Lateral position (m)')

def uncertainty(p, progress):
    rng = np.random.default_rng(p['seed'])
    n = p['samples']
    # Independent calibration and test draws; no calibration on evaluation data.
    calibration = np.abs(rng.normal(0, p['noise'], n))
    errors = rng.normal(p['bias'], p['noise'] * p['shift'], n)
    radius = pm._finite_upper_quantile(calibration, p['coverage'])
    if p['phase'] == 'phase12':
        scales_cal = rng.uniform(.5, 1.5, n)
        scales_test = rng.uniform(.5, 1.5, n)
        radius = pm._finite_upper_quantile(calibration / scales_cal, p['coverage']) * scales_test
    widths = np.broadcast_to(radius, (n,))
    if p['phase'] == 'phase11':
        from uav_safety.phase10_calibration import Phase10UncertaintyCalibrator
        calibration_model = Phase10UncertaintyCalibrator.fit(
            [{'source': 'synthetic', 'abs_lateral_error_m': x, 'abs_altitude_error_m': x} for x in calibration], quantile=p['coverage'])
        widths = np.full(n, calibration_model.fallback.sigma_lateral_m)
    covered = np.abs(errors) <= widths
    if p['phase'] in ('phase13a', 'phase13b', 'phase13c'):
        truth = np.sin(np.arange(n) * .15)
        raw = truth + errors
        shifted = pm._lagged(raw, np.full(n, p['lag']))
        errors = shifted - truth
        covered = np.abs(errors) <= widths
    rows = [{'Sample': i, 'Signed error (m)': errors[i], 'Half-width (m)': widths[i], 'Covered': bool(covered[i])} for i in range(n)]
    metrics = [metric('Empirical coverage', np.mean(covered) * 100, '%'), metric('Requested coverage', p['coverage'] * 100, '%'), metric('Mean interval half-width', np.mean(widths), 'm')]
    result = output('Uncertainty under distribution shift', metrics, rows, [series('Signed test error', errors), series('Upper bound', widths), series('Lower bound', -widths)], 'Core-method exercise: Phase 11 uses the original source-aware calibration component, Phase 12 normalizes scores before finite-sample calibration, and Phase 13 uses the original staleness operator. Synthetic calibration/test samples are independent. These are not the frozen fitted candidates or full phase evaluations.')
    if p['phase'] == 'phase13b':
        result['metrics'].append(metric('Paired coverage change', (np.mean(covered) - np.mean(np.abs(raw-truth) <= widths))*100, 'pp'))
    if p['phase'] == 'phase13c':
        result['attribution'] = {'staleness_coverage_loss': float(np.mean(np.abs(raw-truth)<=widths)-np.mean(covered))}
        result['note'] += ' The attribution reports paired coverage loss from staleness only, not the full compound-factor study.'
    return result

def residual(p, progress):
    rng = np.random.default_rng(p['seed'])
    n = p['samples']
    truth = np.sin(np.arange(n) * .12)
    observed = truth + rng.normal(0, p['noise'], n)
    stale = pm._lagged(observed, np.full(n, p['lag']))
    errors = stale - truth
    e0, e1 = errors[:-1], errors[1:]
    r0 = e1 - p['coefficient'] * e0
    r1 = e1 - p['alternative'] * e0
    bound = pm._finite_upper_quantile(np.abs(r0), p['coverage'])
    minimum_radius = bound / (1 - abs(p['coefficient']))
    rows = [{'Transition': i, 'Current error (m)': e0[i], 'Next error (m)': e1[i], 'Reference residual (m)': r0[i], 'Alternative residual (m)': r1[i]} for i in range(n - 1)]
    if p['phase'] in ('phase14', 'phase15'):
        metrics = [metric('Residual bound', bound, 'm'), metric('Minimum invariant half-width', minimum_radius, 'm'), metric('Chosen half-width', p['radius'], 'm')]
        note = f'The chosen interval {"meets" if p["radius"] >= minimum_radius else "does not meet"} the scalar bound |a| R + w ≤ R. This is an analytical surrogate test, not a full-plant safety proof.'
    else:
        metrics = [metric('Reference residual RMSE', np.sqrt(np.mean(r0 ** 2)), 'm'), metric('Alternative residual RMSE', np.sqrt(np.mean(r1 ** 2)), 'm'), metric('Stale level RMSE', np.sqrt(np.mean(errors ** 2)), 'm')]
        note = 'Custom coefficient comparison on a new synthetic staleness trace. Uses the original lag operator and finite quantile with the published residual equation e₁ − a·e₀. It does not refit a frozen candidate or change any phase verdict.'
    return output('Recoverability and residual dynamics', metrics, rows, [series('Reference residual', r0), series('Alternative residual', r1)], note, 'Transition')

def context(p, progress):
    # A user-defined factorial response surface, never the frozen observed cube.
    rng = np.random.default_rng(p['seed'])
    subsets = pm._all_subsets()
    surface = {s: .2 - sum(p[f] for f in s) - p['interaction'] * ('edge' in s and 'oblique' in s) for s in subsets}
    shapley = pm._shapley_attenuation(surface)
    if np.ptp(list(surface.values())) < 1e-12:
        return output('Constant context surface', [metric('Context cells', 32), metric('Endpoint attenuation', 0, 'pp')], [{'Context': pm._subset_key(s), 'Advantage': v} for s, v in surface.items()], note='All effects are zero. Variance shares are undefined for a constant surface; increase an effect to analyze its structure.')
    spectrum = pm._walsh_spectrum(surface)
    model = pm._model_from_spectrum(spectrum)
    # Model fixed from the input construction; fresh noise is used only at evaluation.
    observed = np.array([surface[s] + rng.normal(0, p['noise']) for s in subsets])
    predictions = np.array([pm._predict(model, s) for s in subsets])
    sse = float(np.sum((observed - predictions) ** 2))
    sst = float(np.sum((observed - np.mean(observed)) ** 2))
    rows = [{'Context': pm._subset_key(s), 'Constructed advantage': surface[s], 'Fresh noisy observation': observed[i], 'Fixed additive prediction': predictions[i]} for i, s in enumerate(subsets)]
    if p['phase'] == 'phase20':
        metrics = [metric('Endpoint attenuation', shapley['endpoint_attenuation'] * 100, 'pp'), metric('Shapley efficiency error', shapley['efficiency_abs_error']), metric('Context cells', 32)]
    elif p['phase'] == 'phase21':
        metrics = [metric('First-order variance', spectrum['first_order_variance_share'] * 100, '%'), metric('Interaction variance', spectrum['interaction_variance_share'] * 100, '%'), metric('Parseval error', spectrum['parseval_abs_error'])]
    else:
        metrics = [metric('Prediction R²', 1 - sse / sst if sst > 0 else 0), metric('Prediction RMSE', np.sqrt(sse / 32)), metric('Context cells', 32)]
    result = output('Five-factor context experiment', metrics, rows, [series('Fresh observation', observed), series('Fixed additive prediction', predictions)], 'Runs the original Phase 20 Shapley, Phase 21 Walsh, and Phase 22 prediction functions on your constructed 32-cell surface. Effects are user-defined; these are not the published frozen coefficients or final results.', 'Context cell', 'Residual advantage')
    result['attribution'] = shapley['contributions']
    return result

def run(raw, progress=lambda done, total: None):
    p = validated(raw)
    phase = p['phase']
    if phase == 'phase4':
        raise ValueError('Phase 4 is a documented provenance gap. No experiment exists to run.')
    if phase in ('phase1', 'phase2', 'phase3', 'phase5'):
        result = landing(p, progress)
    elif phase in ('phase6', 'phase6b'):
        result = camera(p, progress)
    elif phase == 'phase7':
        result = dynamics(p, progress)
    elif phase in ('phase10', 'phase10r'):
        result = temporal(p, progress)
    elif phase in ('phase11', 'phase12', 'phase13a', 'phase13b', 'phase13c'):
        result = uncertainty(p, progress)
    elif phase in ('phase14', 'phase15', 'phase16', 'phase17', 'phase18', 'phase19'):
        result = residual(p, progress)
    elif phase in ('phase20', 'phase21', 'phase22'):
        result = context(p, progress)
    else:
        # Phase 8/9 trace and geometry component diagnostics on synthetic inputs.
        rng = np.random.default_rng(p['seed'])
        a = rng.normal(0, p['noise'], p['samples'])
        b = a * p['shift'] + p['bias']
        rows = [{'Sample': i, 'Reference error (m)': a[i], 'Shifted error (m)': b[i]} for i in range(len(a))]
        result = output('Synthetic trace discrepancy', [metric('Reference RMSE', np.sqrt(np.mean(a*a)), 'm'), metric('Distribution KS distance', pm._empirical_ks(a,b)), metric('Quantile distance', pm._quantile_w1(a,b), 'm')], rows, [series('Reference error', a), series('Shifted error', b)], 'Runs the original Phase 8 distribution-distance functions on a newly generated pair of error traces. Full PX4/Gazebo validation requires external simulator evidence.')
        if phase == 'phase9':
            result['title'] = 'Camera-error sensitivity diagnostic'
            result['metrics'] = [metric('Lateral bias', np.mean(b), 'm'), metric('Shifted error p95', np.quantile(np.abs(b),.95), 'm'), metric('Within 0.45 m', np.mean(np.abs(b)<=.45)*100, '%')]
            result['note'] = 'A synthetic error-distribution sensitivity exercise for interpreting camera traces. This does not execute ArUco/PnP detection or capture Gazebo frames; the full Phase 9 pipeline requires those external inputs.'
    result.update({'schema': 'aegisland.browser-experiment.v1', 'phase': phase, 'inputs': p, 'exploratory': True, 'simulation_only': True, 'frozen_evidence_modified': False, 'runtime': 'Python + NumPy', 'source_commit': '668d065f4312e33e2d21ca7a7ee76d4d6d5617b3'})
    return json.loads(json.dumps(result, allow_nan=False, default=lambda x: x.item() if hasattr(x, 'item') else str(x)))
