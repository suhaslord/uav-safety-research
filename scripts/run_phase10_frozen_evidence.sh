#!/usr/bin/env bash
set -euo pipefail
: "${PHASE10_FROZEN_IMPLEMENTATION:?PHASE10_FROZEN_IMPLEMENTATION must be set}"
: "${GITHUB_SHA:=$(git rev-parse HEAD)}"
ROOT=/tmp/phase10-evidence
PHASE9_RUNNER=/tmp/phase10_phase9_frontend_runner.sh
CALIBRATION=results/phase10_development_seen/calibration.json
printf '%s\n' '== Phase 10 frozen implementation boundary =='
git merge-base --is-ancestor "$PHASE10_FROZEN_IMPLEMENTATION" HEAD
git diff --exit-code "$PHASE10_FROZEN_IMPLEMENTATION" -- src/uav_safety/phase10_metric.py src/uav_safety/phase10_calibration.py scripts/run_phase10_metric_benchmark.py results/phase10_development_seen/calibration.json
printf '%s\n' '== Construct unchanged Phase 9 camera front-end runner for new holdout trajectory =='
python - <<'PY'
from pathlib import Path
source=Path('scripts/run_phase9_gazebo_camera_evidence.sh').read_text(encoding='utf-8')
source=source.replace('/tmp/phase9-evidence','/tmp/phase10-evidence')
source=source.replace('python scripts/run_phase9_gazebo_camera_mission.py','python scripts/run_phase10_gazebo_camera_mission.py')
source=source.replace("assert len(mission.get('segments', [])) == 9","assert len(mission.get('segments', [])) == 11")
Path('/tmp/phase10_phase9_frontend_runner.sh').write_text(source,encoding='utf-8')
PY
chmod +x "$PHASE9_RUNNER"
bash "$PHASE9_RUNNER"
printf '%s\n' '== Frozen AegisT10 paired holdout evaluation =='
python scripts/run_phase10_metric_benchmark.py "$ROOT/analysis/perception_trace.csv" "$ROOT/analysis/detection_details.csv" --out "$ROOT/phase10" --evidence-role phase10_holdout_unseen --calibration "$CALIBRATION"
printf '%s\n' '== Phase 10 scientific boundary and receipt =='
python - <<'PY'
from hashlib import sha256
import json,os
from pathlib import Path
root=Path('/tmp/phase10-evidence'); result=json.loads((root/'phase10/result.json').read_text()); mission=json.loads((root/'px4_mission_metadata.json').read_text()); baseline=json.loads((root/'analysis/scientific_result.json').read_text())
assert mission['mission']=='phase10_frozen_holdout_trajectory_v1' and mission['evidence_role']=='phase10_holdout_unseen' and mission['completed'] is True and len(mission['segments'])==11
assert result['evidence_role']=='phase10_holdout_unseen' and result['simulation_only'] is True and result['safety_acceptance'] is False and result['controller_tuning_allowed'] is False and baseline['simulation_only'] is True
def h(path): return sha256(path.read_bytes()).hexdigest()
assert result['inputs']['trace_sha256']==h(root/'analysis/perception_trace.csv'); assert result['inputs']['detection_details_sha256']==h(root/'analysis/detection_details.csv')
receipt={'schema':'aegisland.phase10.frozen-evidence-receipt.v1','phase10_freeze_marker_sha':os.environ.get('GITHUB_SHA') or '','phase10_frozen_implementation_sha':os.environ['PHASE10_FROZEN_IMPLEMENTATION'],'phase10_evidence_role':'phase10_holdout_unseen','simulation_only':True,'safety_acceptance':False,'controller_tuning_allowed':False,'mission_metadata_sha256':h(root/'px4_mission_metadata.json'),'raw_capture_metadata_sha256':h(root/'capture/capture_frames.csv'),'raw_ulog_sha256':h(root/'px4_gazebo_raw.ulg'),'phase9_frontend_trace_sha256':h(root/'analysis/perception_trace.csv'),'phase9_frontend_detection_details_sha256':h(root/'analysis/detection_details.csv'),'phase10_result_sha256':h(root/'phase10/result.json'),'phase10_per_frame_sha256':h(root/'phase10/per_frame.csv'),'phase10_result_manifest_sha256':h(root/'phase10/result_manifest.json'),'frozen_calibration_sha256':h(Path('results/phase10_development_seen/calibration.json')),'minimum_substantial_win_gate_all':result['minimum_substantial_win_gate_all'],'minimum_substantial_win_gate':result['minimum_substantial_win_gate']}
(root/'phase10/phase10_evidence_receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print(json.dumps({'phase9_baseline':result['phase9_baseline'],'phase10':result['phase10'],'relative_reductions':result['relative_reductions'],'uncertainty':result['uncertainty'],'minimum_substantial_win_gate_all':result['minimum_substantial_win_gate_all']},indent=2,sort_keys=True))
PY
