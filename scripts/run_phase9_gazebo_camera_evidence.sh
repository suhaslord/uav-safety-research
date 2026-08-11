#!/usr/bin/env bash
set -euo pipefail

EVIDENCE_ROOT=/tmp/phase9-evidence
PX4_ROOT=/tmp/PX4-Autopilot
CAPTURE_ROOT="$EVIDENCE_ROOT/capture"
ANALYSIS_ROOT="$EVIDENCE_ROOT/analysis"
mkdir -p "$EVIDENCE_ROOT" "$CAPTURE_ROOT" "$ANALYSIS_ROOT"

: "${PX4_RELEASE:=v1.17.0}"
: "${PX4_SIMULATOR_MODEL:=gz_x500_mono_cam_down}"
: "${PX4_GZ_WORLD:=aruco}"
: "${PHASE9_PARENT_MAIN:=babd4d9849c4792ff1cc002c51cc5dbbc6ed0221}"
: "${PHASE8_FROZEN_HEAD:=bd62e3b31431306fd9d897f560be7325d711d21a}"
: "${PHASE6B_FROZEN_HEAD:=b4e9838555e935a5ec42690495315473629b58f6}"
: "${GITHUB_SHA:=$(git rev-parse HEAD)}"

PX4_MAKE_PID=""
CAPTURE_PID=""

stop_capture() {
  if [[ -n "${CAPTURE_PID:-}" ]] && kill -0 "$CAPTURE_PID" 2>/dev/null; then
    kill -TERM "$CAPTURE_PID" 2>/dev/null || true
    for _ in $(seq 1 30); do
      kill -0 "$CAPTURE_PID" 2>/dev/null || break
      sleep 0.2
    done
    kill -KILL "$CAPTURE_PID" 2>/dev/null || true
    wait "$CAPTURE_PID" 2>/dev/null || true
  fi
}

stop_px4() {
  if [[ -n "${PX4_MAKE_PID:-}" ]] && kill -0 "$PX4_MAKE_PID" 2>/dev/null; then
    kill "$PX4_MAKE_PID" 2>/dev/null || true
    wait "$PX4_MAKE_PID" 2>/dev/null || true
  fi
}

cleanup() {
  stop_capture
  stop_px4
}
trap cleanup EXIT

printf '%s\n' '== Phase 9 frozen-boundary verification =='
test "$PX4_SIMULATOR_MODEL" = "gz_x500_mono_cam_down"
test "$PX4_GZ_WORLD" = "aruco"
git merge-base --is-ancestor "$PHASE9_PARENT_MAIN" HEAD
git merge-base --is-ancestor "$PHASE8_FROZEN_HEAD" HEAD
git merge-base --is-ancestor "$PHASE6B_FROZEN_HEAD" HEAD
git diff --exit-code "$PHASE9_PARENT_MAIN" -- \
  src/uav_safety/trace_validation.py \
  src/uav_safety/external_trace.py \
  scripts/run_phase8_trace_validation.py \
  src/uav_safety/phase6b_fusion.py \
  src/uav_safety/simulator_image_phase6b.py \
  scripts/run_phase6b_landing.py \
  docs/phase6b_freeze_manifest.md \
  results/phase6b_frozen_landing \
  results/phase6b_frozen_selective

printf '%s\n' '== Exact-head compile and tests =='
python -m compileall -q src scripts tests
pytest -q

printf '%s\n' '== Frozen Phase 7 surrogate reference =='
python scripts/export_phase7_surrogate_trace.py \
  --seed 979797 \
  --calibration-seed 616161 \
  --condition clean \
  --out "$EVIDENCE_ROOT/phase7_surrogate.csv" \
  --metadata-out "$EVIDENCE_ROOT/phase7_surrogate_metadata.json"

printf '%s\n' '== Pinned PX4 / Gazebo environment =='
git clone --branch "$PX4_RELEASE" --depth 1 --recursive \
  https://github.com/PX4/PX4-Autopilot.git "$PX4_ROOT"
git -C "$PX4_ROOT" rev-parse HEAD | tee "$EVIDENCE_ROOT/px4_git_sha.txt"
sudo env DEBIAN_FRONTEND=noninteractive bash "$PX4_ROOT/Tools/setup/ubuntu.sh" --no-nuttx
python -m pip install -r "$PX4_ROOT/Tools/setup/requirements.txt"
python - <<'PY'
import kconfiglib
print(f"kconfiglib active interpreter OK: {kconfiglib.__file__}")
PY

printf '%s\n' '== Compile Gazebo transport raw-camera collector =='
TRANSPORT_PKG="$(pkg-config --list-all | awk '$1 ~ /^gz-transport[0-9]+$/ {print $1}' | sort -V | tail -1)"
MSGS_PKG="$(pkg-config --list-all | awk '$1 ~ /^gz-msgs[0-9]+$/ {print $1}' | sort -V | tail -1)"
test -n "$TRANSPORT_PKG"
test -n "$MSGS_PKG"
printf 'transport_pkg=%s\nmsgs_pkg=%s\n' "$TRANSPORT_PKG" "$MSGS_PKG" | tee "$EVIDENCE_ROOT/gazebo_pkg_config.txt"
g++ -std=c++17 -O2 -Wall -Wextra -pedantic \
  tools/phase9_gz_camera_capture.cc \
  -o /tmp/phase9_gz_camera_capture \
  $(pkg-config --cflags --libs "$TRANSPORT_PKG" "$MSGS_PKG") \
  -pthread

printf '%s\n' '== Start PX4 SITL downward camera / ArUco world =='
touch "$EVIDENCE_ROOT/px4_run_started"
(
  cd "$PX4_ROOT"
  export HEADLESS=1
  export LIBGL_ALWAYS_SOFTWARE=1
  export PX4_SIM_SPEED_FACTOR=1
  export PX4_GZ_WORLD="$PX4_GZ_WORLD"
  export PX4_PARAM_SDLOG_PROFILE=129
  export PX4_PARAM_COM_RCL_EXCEPT=4
  make px4_sitl "$PX4_SIMULATOR_MODEL" </dev/null > "$EVIDENCE_ROOT/px4_gazebo.log" 2>&1
) &
PX4_MAKE_PID=$!
printf '%s\n' "$PX4_MAKE_PID" > "$EVIDENCE_ROOT/px4_make.pid"

ready=0
for _ in $(seq 1 480); do
  if ! kill -0 "$PX4_MAKE_PID" 2>/dev/null; then
    echo 'PX4 SITL launch process exited before readiness'
    tail -n 300 "$EVIDENCE_ROOT/px4_gazebo.log" || true
    exit 1
  fi
  if grep -q 'Startup script returned successfully' "$EVIDENCE_ROOT/px4_gazebo.log"; then
    ready=1
    break
  fi
  sleep 1
done
if [[ "$ready" -ne 1 ]]; then
  echo 'PX4 SITL did not report startup readiness within 480 seconds'
  tail -n 300 "$EVIDENCE_ROOT/px4_gazebo.log" || true
  exit 1
fi

printf '%s\n' '== Discover live Gazebo camera and child-link pose topics =='
python - <<'PY'
from pathlib import Path
import os
import subprocess
import time

root = Path('/tmp/phase9-evidence')
world = os.environ.get('PX4_GZ_WORLD', 'aruco')
topics = []
for _ in range(90):
    proc = subprocess.run(['gz', 'topic', '-l'], text=True, capture_output=True)
    topics = sorted({line.strip() for line in proc.stdout.splitlines() if line.strip()})
    if any(topic.endswith('/image') for topic in topics) and any(topic.endswith('/pose/info') for topic in topics):
        break
    time.sleep(1)
(root / 'gazebo_topics.txt').write_text('\n'.join(topics) + '\n', encoding='utf-8')
assert topics, 'Gazebo topic graph is empty'

def info(topic: str) -> str:
    proc = subprocess.run(['gz', 'topic', '-i', '-t', topic], text=True, capture_output=True)
    return (proc.stdout + '\n' + proc.stderr).strip()

image_candidates = []
for topic in topics:
    if not topic.endswith('/image'):
        continue
    detail = info(topic)
    if 'Image' not in detail:
        continue
    lower = topic.lower()
    score = 0
    score += 10 if 'mono_cam' in lower else 0
    score += 6 if 'x500' in lower else 0
    score += 4 if 'camera' in lower else 0
    image_candidates.append((score, topic, detail))
assert image_candidates, 'No gz.msgs.Image camera topic discovered'
image_candidates.sort(key=lambda item: (-item[0], item[1]))
camera_topic = image_candidates[0][1]

pose_candidates = []
for topic in topics:
    if not topic.endswith('/pose/info') and not topic.endswith('/dynamic_pose/info'):
        continue
    detail = info(topic)
    if 'Pose' not in detail:
        continue
    # The diagnostic run proved dynamic_pose/info omitted the fixed camera link.
    # Prefer the regular child-link pose stream; dynamic_pose remains a fallback.
    score = 20 if topic.endswith('/pose/info') and not topic.endswith('/dynamic_pose/info') else 5
    score += 4 if f'/world/{world}/' in topic else 0
    pose_candidates.append((score, topic, detail))
assert pose_candidates, 'No Gazebo Pose_V topic discovered'
pose_candidates.sort(key=lambda item: (-item[0], item[1]))
pose_topic = pose_candidates[0][1]
assert not pose_topic.endswith('/dynamic_pose/info'), (
    f'only dynamic pose stream selected; fixed camera-link pose is unavailable: {pose_topic}'
)

(root / 'camera_topic.txt').write_text(camera_topic + '\n', encoding='utf-8')
(root / 'pose_topic.txt').write_text(pose_topic + '\n', encoding='utf-8')
(root / 'camera_topic_info.txt').write_text(image_candidates[0][2] + '\n', encoding='utf-8')
(root / 'pose_topic_info.txt').write_text(pose_candidates[0][2] + '\n', encoding='utf-8')
(root / 'topic_selection.json').write_text(
    __import__('json').dumps(
        {
            'camera_topic': camera_topic,
            'pose_topic': pose_topic,
            'camera_candidate_count': len(image_candidates),
            'pose_candidate_count': len(pose_candidates),
            'pose_policy': 'regular_pose_info_preferred_for_fixed_camera_link',
        },
        indent=2,
        sort_keys=True,
    ) + '\n',
    encoding='utf-8',
)
print(f'camera_topic={camera_topic}')
print(f'pose_topic={pose_topic}')
PY

printf '%s\n' '== Start exact raw pixel capture =='
CAMERA_TOPIC="$(cat "$EVIDENCE_ROOT/camera_topic.txt")"
POSE_TOPIC="$(cat "$EVIDENCE_ROOT/pose_topic.txt")"
# The diagnostics-only first run received 560 genuine image messages but saved
# only 19 at stride 30. A stride of 10 is a capture-density correction made
# before any scientific analysis; it does not change the frozen detector or metrics.
/tmp/phase9_gz_camera_capture \
  "$CAMERA_TOPIC" \
  "$POSE_TOPIC" \
  "$CAPTURE_ROOT" \
  10 \
  90 \
  > "$EVIDENCE_ROOT/camera_capture.log" 2>&1 &
CAPTURE_PID=$!
printf '%s\n' "$CAPTURE_PID" > "$EVIDENCE_ROOT/camera_capture.pid"
sleep 3
kill -0 "$CAPTURE_PID"

printf '%s\n' '== Run predeclared simulation-only visibility sweep =='
set +e
timeout --signal=TERM --kill-after=15s 300s \
  python scripts/run_phase9_gazebo_camera_mission.py \
    --connection udpin://0.0.0.0:14550 \
    --metadata-out "$EVIDENCE_ROOT/px4_mission_metadata.json"
MISSION_STATUS=$?
set -e
if [[ "$MISSION_STATUS" -ne 0 ]]; then
  echo "Phase 9 PX4/Gazebo camera mission failed or timed out with status $MISSION_STATUS"
  tail -n 300 "$EVIDENCE_ROOT/px4_gazebo.log" || true
  tail -n 200 "$EVIDENCE_ROOT/camera_capture.log" || true
  exit "$MISSION_STATUS"
fi
sleep 3
stop_capture
CAPTURE_PID=""
tail -n 100 "$EVIDENCE_ROOT/camera_capture.log" || true

printf '%s\n' '== Genuine frame / camera-pose sanity gate =='
test -s "$CAPTURE_ROOT/capture_frames.csv"
python - <<'PY'
from pathlib import Path
import json
import pandas as pd

root = Path('/tmp/phase9-evidence')
frame = pd.read_csv(root / 'capture/capture_frames.csv')
pose_valid = frame['camera_pose_valid'].astype(str).str.lower().isin({'true', '1', 'yes'})
existing = [(root / 'capture' / path).is_file() for path in frame['frame_path'].astype(str)]
assert len(frame) >= 20, f'too few selected raw camera frames: {len(frame)}'
assert int(pose_valid.sum()) >= 20, f'too few frames with synchronized camera pose: {int(pose_valid.sum())}'
assert all(existing), 'one or more selected raw camera payload files are missing'
assert int(frame['data_size'].min()) > 0, 'camera payload contains an empty image'
valid_names = sorted(set(frame.loc[pose_valid, 'camera_pose_name'].dropna().astype(str)))
assert valid_names, 'no camera pose entity names recorded'
assert all('camera_link' in name for name in valid_names), valid_names
sanity = {
    'selected_raw_frames': int(len(frame)),
    'frames_with_camera_pose': int(pose_valid.sum()),
    'camera_pose_names': valid_names,
    'image_width_px': sorted({int(v) for v in frame['width']}),
    'image_height_px': sorted({int(v) for v in frame['height']}),
    'raw_payload_bytes_min': int(frame['data_size'].min()),
    'raw_payload_bytes_max': int(frame['data_size'].max()),
    'image_message_index_first': int(frame['image_message_index'].iloc[0]),
    'image_message_index_last': int(frame['image_message_index'].iloc[-1]),
}
(root / 'camera_capture_sanity.json').write_text(json.dumps(sanity, indent=2, sort_keys=True) + '\n')
print(json.dumps(sanity, indent=2))
PY

printf '%s\n' '== Stop simulator and locate same-run PX4 ULog =='
sleep 3
stop_px4
PX4_MAKE_PID=""
sleep 2
LOG_ROOT="$PX4_ROOT/build/px4_sitl_default/rootfs/log"
test -d "$LOG_ROOT"
find "$LOG_ROOT" -type f -name '*.ulg' -newer "$EVIDENCE_ROOT/px4_run_started" -print | sort | tee "$EVIDENCE_ROOT/ulog_candidates.txt"
ULOG="$(find "$LOG_ROOT" -type f -name '*.ulg' -newer "$EVIDENCE_ROOT/px4_run_started" -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2-)"
test -n "$ULOG"
test -f "$ULOG"
printf '%s\n' "$ULOG" > "$EVIDENCE_ROOT/px4_ulog_source_path.txt"
cp "$ULOG" "$EVIDENCE_ROOT/px4_gazebo_raw.ulg"

printf '%s\n' '== Completed-mission / ULog provenance gate =='
python - <<'PY'
import json
from pathlib import Path
import numpy as np
from pyulog import ULog

root = Path('/tmp/phase9-evidence')
mission = json.loads((root / 'px4_mission_metadata.json').read_text())
assert mission.get('completed') is True
assert len(mission.get('segments', [])) == 9
ulog = ULog(str(root / 'px4_gazebo_raw.ulg'))
datasets = {d.name: d for d in ulog.data_list}
for name in ('vehicle_status', 'vehicle_local_position_groundtruth', 'vehicle_local_position'):
    assert name in datasets, f'ULog missing {name}'
truth = datasets['vehicle_local_position_groundtruth'].data
ts = np.asarray(truth['timestamp'], dtype=float) * 1e-6
assert ts.size >= 100
assert float(ts[-1] - ts[0]) >= 20.0
sanity = {
    'mission_completed': True,
    'ulog_start_timestamp_us': int(ulog.start_timestamp),
    'ulog_last_timestamp_us': int(ulog.last_timestamp),
    'groundtruth_samples': int(ts.size),
    'groundtruth_duration_s': float(ts[-1] - ts[0]),
}
(root / 'px4_ulog_sanity.json').write_text(json.dumps(sanity, indent=2, sort_keys=True) + '\n')
print(json.dumps(sanity, indent=2))
PY

printf '%s\n' '== Frozen Phase 9 genuine-frame analysis =='
python scripts/analyze_phase9_gazebo_camera_evidence.py \
  "$CAPTURE_ROOT/capture_frames.csv" \
  --frame-root "$CAPTURE_ROOT" \
  --out "$ANALYSIS_ROOT" \
  --camera-topic-file "$EVIDENCE_ROOT/camera_topic.txt" \
  --pose-topic-file "$EVIDENCE_ROOT/pose_topic.txt" \
  --px4-git-sha-file "$EVIDENCE_ROOT/px4_git_sha.txt" \
  --px4-release "$PX4_RELEASE" \
  --simulator-model "$PX4_SIMULATOR_MODEL" \
  --simulator-world "$PX4_GZ_WORLD" \
  --git-sha "$GITHUB_SHA" \
  --horizontal-fov-rad 1.74 \
  --marker-size-m 0.5 \
  --surrogate-trace "$EVIDENCE_ROOT/phase7_surrogate.csv"

printf '%s\n' '== Hash and scientific-role validation =='
python scripts/validate_phase9_perception_trace.py \
  "$ANALYSIS_ROOT/perception_trace.csv" \
  --frame-root "$CAPTURE_ROOT" \
  --verify-frame-hashes \
  --summary-out "$ANALYSIS_ROOT/validation_summary.json"

python - <<'PY'
from hashlib import sha256
import json
from pathlib import Path

root = Path('/tmp/phase9-evidence')
result = json.loads((root / 'analysis/scientific_result.json').read_text())
manifest = json.loads((root / 'analysis/result_manifest.json').read_text())
summary = json.loads((root / 'analysis/validation_summary.json').read_text())
assert result['external_perception_evidence_status'] == 'external_perception_seen'
assert result['claim_level'] == 'descriptive_external_perception_seen'
assert result['classification_thresholds_declared'] is False
assert result['resemblance_verdict'] is None
assert result['safety_acceptance'] is False
assert result['controller_tuning_allowed'] is False
assert result['simulation_only'] is True
assert result['validation']['rows'] >= 20
assert result['validation']['verified_frame_hashes'] == result['validation']['rows']
assert result['validation']['target_visible_rate'] > 0
assert summary['validation']['verified_frame_hashes'] == result['validation']['rows']
assert manifest['schema'] == 'aegisland.phase9.perception-result.v1'
for name, record in manifest['files'].items():
    path = root / 'analysis' / name
    assert path.stat().st_size == record['bytes']
    assert sha256(path.read_bytes()).hexdigest() == record['sha256']
PY

printf '%s\n' '== Exact-head evidence receipt =='
python - <<'PY'
from hashlib import sha256
import json
import os
from pathlib import Path

root = Path('/tmp/phase9-evidence')
def h(relative: str) -> str:
    return sha256((root / relative).read_bytes()).hexdigest()

result = json.loads((root / 'analysis/scientific_result.json').read_text())
capture = json.loads((root / 'camera_capture_sanity.json').read_text())
ulog = json.loads((root / 'px4_ulog_sanity.json').read_text())
receipt = {
    'aegis_phase9_head_sha': os.environ.get('GITHUB_SHA') or os.popen('git rev-parse HEAD').read().strip(),
    'phase9_parent_main': os.environ['PHASE9_PARENT_MAIN'],
    'frozen_phase8_head': os.environ['PHASE8_FROZEN_HEAD'],
    'historical_phase6b_frozen_commit': os.environ['PHASE6B_FROZEN_HEAD'],
    'github_workflow': os.environ.get('GITHUB_WORKFLOW'),
    'github_run_id': os.environ.get('GITHUB_RUN_ID'),
    'github_run_attempt': os.environ.get('GITHUB_RUN_ATTEMPT'),
    'px4_release': os.environ['PX4_RELEASE'],
    'px4_git_sha': (root / 'px4_git_sha.txt').read_text().strip(),
    'simulator_model': os.environ['PX4_SIMULATOR_MODEL'],
    'simulator_world': os.environ['PX4_GZ_WORLD'],
    'camera_topic': (root / 'camera_topic.txt').read_text().strip(),
    'pose_topic': (root / 'pose_topic.txt').read_text().strip(),
    'capture_stride_messages': 10,
    'camera_capture_sanity': capture,
    'px4_ulog_sanity': ulog,
    'external_perception_evidence_status': result['external_perception_evidence_status'],
    'claim_level': result['claim_level'],
    'classification_thresholds_declared': result['classification_thresholds_declared'],
    'resemblance_verdict': result['resemblance_verdict'],
    'safety_acceptance': result['safety_acceptance'],
    'controller_tuning_allowed': result['controller_tuning_allowed'],
    'simulation_only': result['simulation_only'],
    'raw_capture_metadata_sha256': h('capture/capture_frames.csv'),
    'raw_ulog_sha256': h('px4_gazebo_raw.ulg'),
    'mission_metadata_sha256': h('px4_mission_metadata.json'),
    'scientific_result_sha256': h('analysis/scientific_result.json'),
    'perception_trace_sha256': h('analysis/perception_trace.csv'),
    'result_manifest_sha256': h('analysis/result_manifest.json'),
    'phase7_surrogate_sha256': h('phase7_surrogate.csv'),
}
assert receipt['external_perception_evidence_status'] == 'external_perception_seen'
assert receipt['classification_thresholds_declared'] is False
assert receipt['resemblance_verdict'] is None
assert receipt['safety_acceptance'] is False
assert receipt['controller_tuning_allowed'] is False
(root / 'phase9_camera_evidence_receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
print(json.dumps(receipt, indent=2))
PY

printf '%s\n' '== Phase 9 genuine Gazebo camera evidence completed =='
cat "$ANALYSIS_ROOT/summary.md"
