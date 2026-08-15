from __future__ import annotations

import json
from scripts.generate_phase10_fixture import generate
from scripts.run_phase10_metric_benchmark import run_benchmark


def test_phase10_fixture_pipeline_is_paired_and_non_authoritative(tmp_path):
    fixture=tmp_path/"fixture"; output=tmp_path/"output"; generate(fixture,seed=101010,frames=72); result=run_benchmark(fixture/"perception_trace.csv",fixture/"detection_details.csv",output,evidence_role="phase10_development_seen",calibration_path=None,fit_calibration=True); assert result["simulation_only"] is True; assert result["safety_acceptance"] is False; assert result["controller_tuning_allowed"] is False; assert result["phase10"]["lateral"]["mae"]<result["phase9_baseline"]["lateral"]["mae"]; assert result["phase10"]["altitude"]["mae"]<result["phase9_baseline"]["altitude"]["mae"]; assert (output/"result_manifest.json").is_file(); payload=json.loads((output/"result.json").read_text()); assert payload["evidence_role"]=="phase10_development_seen"
