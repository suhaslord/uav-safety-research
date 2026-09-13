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

def test_frozen_landing_runner_is_used(lab):
    from uav_safety.config import SimConfig
    from uav_safety.perception import PROFILES
    from uav_safety.simulator import run_episode
    from dataclasses import replace
    p=lab.validated({'phase':'phase1','episodes':1})
    profile=replace(PROFILES[p['condition']],dropout_prob=p['dropout'],bias_x=p['bias'],sigma_x=p['noise'])
    original=run_episode(p['seed'],p['condition'],True,sim_cfg=SimConfig(initial_x_range=(p['offset'],)*2,initial_z_range=(p['altitude'],)*2),perception_profile=profile)
    result=lab.run({'phase':'phase1','episodes':1})
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
