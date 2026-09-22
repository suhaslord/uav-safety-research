import importlib
import json
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]

@pytest.fixture(scope='module')
def lab(tmp_path_factory):
    path = tmp_path_factory.mktemp('browser-python')
    bundle = json.loads((ROOT / 'deploy/vercel/lab/python-bundle.json').read_text(encoding='utf-8'))
    for name, content in bundle['files'].items():
        target = path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')
    sys.path.insert(0, str(path))
    return importlib.import_module('browser_experiments')

@pytest.mark.parametrize('phase', ['phase1','phase2','phase3','phase5','phase6','phase6b','phase7','phase8','phase9','phase10','phase10r','phase11','phase12','phase13a','phase13b','phase13c','phase14','phase15','phase16','phase17','phase18','phase19','phase20','phase21','phase22'])
def test_every_runnable_phase_produces_finite_reproducible_results(lab, phase):
    inputs = {'phase': phase, 'samples': 32, 'episodes': 1}
    a, b = lab.run(inputs), lab.run(inputs)
    assert a == b
    assert a['rows'] and a['metrics']
    assert a['exploratory'] and not a['frozen_evidence_modified']
    assert all(np.isfinite(m['value']) for m in a['metrics'])

def test_gap_cannot_produce_fabricated_results(lab):
    with pytest.raises(ValueError, match='provenance gap'):
        lab.run({'phase': 'phase4'})

@pytest.mark.parametrize('key,value', [('seed',-1),('samples',10000000),('noise',float('nan')),('lag',2.5),('coefficient',1),('episodes',True)])
def test_input_limits_are_enforced_by_python(lab, key, value):
    with pytest.raises(ValueError):
        lab.run({'phase':'phase1',key:value})

def test_source_shapley_and_walsh_match_additive_identity(lab):
    pm = importlib.import_module('phase_math')
    effects={f:(i+1)*.01 for i,f in enumerate(pm.FACTORS)}
    cube={s: .2-sum(effects[f] for f in s) for s in pm._all_subsets()}
    attribution=pm._shapley_attenuation(cube)
    for f,v in effects.items():
        assert attribution['contributions'][f] == pytest.approx(v)
    spectrum=pm._walsh_spectrum(cube)
    assert spectrum['first_order_variance_share'] == pytest.approx(1)
    model=pm._model_from_spectrum(spectrum)
    for s,v in cube.items():
        assert pm._predict(model,s) == pytest.approx(v)

def test_changing_inputs_changes_computed_result(lab):
    a=lab.run({'phase':'phase22','noise':.01})
    b=lab.run({'phase':'phase22','noise':1})
    assert a['metrics'][1]['value'] < b['metrics'][1]['value']

@pytest.mark.parametrize('phase', ['phase1','phase2','phase3','phase5'])
def test_frozen_landing_runner_is_used(lab, phase):
    from uav_safety.config import SimConfig
    from uav_safety.perception import PROFILES
    from uav_safety.simulator import run_episode
    from dataclasses import replace
    from uav_safety.simulator_v2 import run_episode_v2
    from uav_safety.simulator_v3 import run_episode_v3
    p=lab.validated({'phase':phase,'episodes':1,'noise':.4,'seed':219})
    profile=replace(PROFILES[p['condition']],dropout_prob=p['dropout'],bias_x=p['bias'],sigma_x=p['noise'])
    cfg=SimConfig(initial_x_range=(p['offset'],)*2,initial_z_range=(p['altitude'],)*2)
    original=run_episode(p['seed'],p['condition'],True,sim_cfg=cfg,perception_profile=profile) if phase=='phase1' else (run_episode_v2 if phase=='phase2' else run_episode_v3)(p['seed'],p['condition'],sim_cfg=cfg,perception_profile=profile)
    result=lab.run(p)
    assert result['rows'][0]['Aegis outcome']==original.outcome
    assert result['rows'][0]['Final lateral error (m)']==original.final_x_error

def test_camera_no_measurements_has_no_error_estimate(lab, monkeypatch):
    from types import SimpleNamespace
    from uav_safety.image_temporal import Phase6PadEstimator
    monkeypatch.setattr(Phase6PadEstimator, 'estimate', lambda self, frame: SimpleNamespace(valid=False, raw_confidence=0))
    result = lab.run({'phase':'phase6', 'samples':32})
    assert result['metrics'][0]['value'] == 0
    assert result['metrics'][2]['value'] is None

def test_observation_noise_does_not_change_structural_analysis(lab):
    a=lab.run({'phase':'phase21', 'noise':.01})
    b=lab.run({'phase':'phase21', 'noise':.5})
    assert a['metrics'] == b['metrics']
    assert a['rows'] != b['rows']

def test_interaction_changes_structural_share(lab):
    a=lab.run({'phase':'phase21', 'interaction':0})
    b=lab.run({'phase':'phase21', 'interaction':.2})
    assert a['metrics'][1]['value'] < 1e-10
    assert b['metrics'][1]['value'] > a['metrics'][1]['value']


def finite_quantile(values, q):
    import math
    return sorted(values)[min(len(values), math.ceil((len(values)+1)*q))-1]


@pytest.mark.parametrize('phase', ['phase6','phase6b'])
def test_camera_matches_original_renderer_and_estimator(lab, phase):
    from uav_safety.image_temporal import Phase6LandingPadRenderer, Phase6PadEstimator
    from uav_safety.selective_confidence_v2 import SharpnessAwarePadEstimator
    p=lab.validated({'phase':phase,'samples':32,'seed':421,'severity':.6})
    rng=np.random.default_rng(p['seed'])
    renderer=Phase6LandingPadRenderer()
    estimator=SharpnessAwarePadEstimator() if phase=='phase6b' else Phase6PadEstimator()
    result=lab.run(p)
    for row in result['rows']:
        m=estimator.estimate(renderer.render(p['offset'],p['altitude'],rng,p['condition'],p['severity']))
        assert row['Available']==m.valid
        assert row['Lateral error (m)']==pytest.approx(m.x_m-p['offset']) if m.valid else row['Lateral error (m)'] is None


def test_dynamics_matches_original_plant(lab):
    from uav_safety.config import SimConfig
    from uav_safety.dynamics import State
    from uav_safety.dynamics_phase7 import Phase7DynamicsConfig, Phase7PlantMemory, step_phase7_dynamics
    p=lab.validated({'phase':'phase7','samples':32,'tau':.7})
    state=State(x=0.,z=p['altitude'],vx=0.,vz=0.)
    memory=Phase7PlantMemory(); rng=np.random.default_rng(p['seed'])
    for i,row in enumerate(lab.run(p)['rows']):
        state,memory=step_phase7_dynamics(state,memory,np.sin(i*.05)*p['severity'],0,0,0,rng,SimConfig(),Phase7DynamicsConfig(actuator_time_constant_s=p['tau']))
        assert row['Lagged-plant x (m)']==state.x


@pytest.mark.parametrize('phase', ['phase10','phase10r'])
def test_temporal_matches_original_estimator(lab, phase):
    from uav_safety.phase10_metric import MetricFrame, run_sequence
    p=lab.validated({'phase':phase,'samples':32,'dropout':.4})
    result=lab.run(p)
    frames=[MetricFrame(i*.1,i,r['Observation (m)'] is not None,r['Observation (m)'],p['altitude'] if r['Observation (m)'] is not None else None,'aruco' if i%5==0 else 'quad_fallback',.5,1400.) for i,r in enumerate(result['rows'])]
    for row,estimate in zip(result['rows'],run_sequence(frames)):
        expected=estimate.lateral_x_m if estimate.metric_estimate_available else None
        assert row['Estimate (m)']==expected


@pytest.mark.parametrize('phase', ['phase8','phase9'])
def test_distribution_metrics_against_independent_definition(lab, phase):
    result=lab.run({'phase':phase,'samples':32,'shift':3})
    a=np.array([r['Reference error (m)'] for r in result['rows']]); b=np.array([r['Shifted error (m)'] for r in result['rows']])
    if phase=='phase8':
        ks=max(abs(np.mean(a<=x)-np.mean(b<=x)) for x in np.concatenate([a,b]))
        expected=[np.sqrt(np.mean(a*a)),ks,np.mean(abs(np.quantile(a,np.linspace(0,1,201))-np.quantile(b,np.linspace(0,1,201))))]
    else: expected=[np.mean(b),np.quantile(abs(b),.95),np.mean(abs(b)<=.45)*100]
    assert [m['value'] for m in result['metrics']]==pytest.approx(expected)


@pytest.mark.parametrize('phase', ['phase11','phase12','phase13a','phase13b','phase13c'])
def test_coverage_against_independent_calibration_and_lag(lab, phase):
    p=lab.validated({'phase':phase,'samples':32,'lag':3,'coverage':.8})
    rng=np.random.default_rng(p['seed']); n=p['samples']
    cal=abs(rng.normal(0,p['noise'],n)); errors=rng.normal(p['bias'],p['noise']*p['shift'],n)
    widths=np.full(n,finite_quantile(cal,p['coverage']))
    if phase=='phase11': widths[:]=max(.03,np.quantile(cal,p['coverage']))
    if phase=='phase12':
        sc=rng.uniform(.5,1.5,n); st=rng.uniform(.5,1.5,n)
        widths=finite_quantile(cal/sc,p['coverage'])*st
    if phase.startswith('phase13'):
        truth=np.sin(np.arange(n)*.15); raw=truth+errors
        errors=np.array([raw[max(0,i-p['lag'])] for i in range(n)])-truth
    result=lab.run(p)
    np.testing.assert_allclose([r['Signed error (m)'] for r in result['rows']],errors)
    np.testing.assert_allclose([r['Half-width (m)'] for r in result['rows']],widths)
    assert result['metrics'][0]['value']==pytest.approx(np.mean(abs(errors)<=widths)*100)


@pytest.mark.parametrize('phase', ['phase14','phase15','phase16','phase17','phase18','phase19'])
def test_residual_equation_and_finite_bound(lab, phase):
    p=lab.validated({'phase':phase,'samples':32,'coefficient':-.4,'alternative':.2})
    result=lab.run(p)
    ref=np.array([r['Next error (m)']-p['coefficient']*r['Current error (m)'] for r in result['rows']])
    alt=np.array([r['Next error (m)']-p['alternative']*r['Current error (m)'] for r in result['rows']])
    np.testing.assert_allclose(result['series'][0]['values'],ref)
    np.testing.assert_allclose(result['series'][1]['values'],alt)
    if phase in ('phase14','phase15'):
        bound=finite_quantile(abs(ref),p['coverage'])
        assert result['metrics'][1]['value']==pytest.approx(bound/(1-abs(p['coefficient'])))
    else: assert result['metrics'][0]['value']==pytest.approx(np.sqrt(np.mean(ref*ref)))


@pytest.mark.parametrize('phase', ['phase20','phase21','phase22'])
def test_context_original_functions_against_factorial_regression(lab, phase):
    pm=importlib.import_module('phase_math')
    p=lab.validated({'phase':phase,'interaction':.12,'noise':.02})
    result=lab.run(p); subsets=pm._all_subsets()
    x=np.array([[1]+[int(f in s) for f in pm.FACTORS] for s in subsets])
    y=np.array([.2-sum(p[f] for f in s)-p['interaction']*('edge' in s and 'oblique' in s) for s in subsets])
    pred=x@np.linalg.lstsq(x,y,rcond=None)[0]
    np.testing.assert_allclose(result['series'][1]['values'],pred,atol=1e-14)
    for f in pm.FACTORS: assert result['attribution'][f]==pytest.approx(p[f]+(p['interaction']/2 if f in ('edge','oblique') else 0))
    if phase=='phase21': assert result['metrics'][0]['value']==pytest.approx(np.var(pred)/np.var(y)*100)
    if phase=='phase22':
        observed=np.array(result['series'][0]['values'])
        assert result['metrics'][0]['value']==pytest.approx(1-np.sum((observed-pred)**2)/np.sum((observed-observed.mean())**2))


def test_bundle_matches_original_modules_and_recorded_function_hashes():
    import ast
    import hashlib
    bundle=json.loads((ROOT/'deploy/vercel/lab/python-bundle.json').read_text(encoding='utf-8'))
    for path in (ROOT/'src/uav_safety').glob('*.py'):
        assert bundle['files']['uav_safety/'+path.name]==path.read_text(encoding='utf-8')
    code=bundle['files']['phase_math.py']; nodes={n.name:n for n in ast.parse(code).body if isinstance(n,ast.FunctionDef)}
    for entry in bundle['provenance']:
        assert hashlib.sha256(ast.get_source_segment(code,nodes[entry['function']]).encode()).hexdigest()==entry['sha256']
