#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 8 ]; then
  echo "usage: $0 PX4_ROOT OUT_ROOT CASE_ID MOTOR EFFECTIVENESS ONSET_S PATH_SEED MODEL_THRUST_SCALE" >&2
  exit 2
fi

PX4_ROOT="$1"; OUT_ROOT="$2"; CASE_ID="$3"; MOTOR="$4"; EFFECTIVENESS="$5"; ONSET_S="$6"; PATH_SEED="$7"; MODEL_THRUST_SCALE="$8"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CASE_DIR="$OUT_ROOT/$CASE_ID"
TRIGGER="$CASE_DIR/fault.trigger"
RECEIPT="$CASE_DIR/fault_receipt.csv"
MARKER="$CASE_DIR/run_started"
mkdir -p "$CASE_DIR"
rm -f "$TRIGGER" "$RECEIPT"
touch "$MARKER"

export HEADLESS=1
export PX4_SIM_SPEED_FACTOR=1
export PX4_PARAM_SDLOG_PROFILE=129
export PX4_PARAM_COM_RCL_EXCEPT=4
export AEGIS_FAULT_MOTOR="$MOTOR"
export AEGIS_FAULT_EFFECTIVENESS="$EFFECTIVENESS"
export AEGIS_MODEL_THRUST_SCALE="$MODEL_THRUST_SCALE"
export AEGIS_FAULT_TRIGGER_FILE="$TRIGGER"
export AEGIS_FAULT_RECEIPT_FILE="$RECEIPT"

cleanup() {
  set +e
  if [ -f "$CASE_DIR/px4_make.pid" ]; then
    kill "$(cat "$CASE_DIR/px4_make.pid")" 2>/dev/null || true
    wait "$(cat "$CASE_DIR/px4_make.pid")" 2>/dev/null || true
  fi
  pkill -f mavsdk_server 2>/dev/null || true
  pkill -f 'gz sim' 2>/dev/null || true
  set -e
}
trap cleanup EXIT

(
  cd "$PX4_ROOT"
  make px4_sitl gz_x500 </dev/null > "$CASE_DIR/px4_gazebo.log" 2>&1
) &
echo $! > "$CASE_DIR/px4_make.pid"

ready=0
for _ in $(seq 1 300); do
  pid="$(cat "$CASE_DIR/px4_make.pid")"
  if ! kill -0 "$pid" 2>/dev/null; then
    echo "PX4 process exited before readiness for $CASE_ID" >&2
    tail -n 200 "$CASE_DIR/px4_gazebo.log" || true
    exit 1
  fi
  if grep -q "Startup script returned successfully" "$CASE_DIR/px4_gazebo.log"; then
    ready=1
    break
  fi
  sleep 1
done
if [ "$ready" -ne 1 ]; then
  echo "PX4 readiness timeout for $CASE_ID" >&2
  tail -n 200 "$CASE_DIR/px4_gazebo.log" || true
  exit 1
fi

python "$REPO_ROOT/scripts/run_ornik_px4_mission.py" \
  --case-id "$CASE_ID" \
  --fault-motor "$MOTOR" \
  --effectiveness "$EFFECTIVENESS" \
  --fault-after-s "$ONSET_S" \
  --model-thrust-scale "$MODEL_THRUST_SCALE" \
  --path-seed "$PATH_SEED" \
  --trigger-file "$TRIGGER" \
  --metadata-out "$CASE_DIR/mission_metadata.json"

sleep 3
cleanup
trap - EXIT

LOG_ROOT="$PX4_ROOT/build/px4_sitl_default/rootfs/log"
ULOG="$(find "$LOG_ROOT" -type f -name '*.ulg' -newer "$MARKER" -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2-)"
if [ -z "$ULOG" ] || [ ! -s "$ULOG" ]; then
  echo "No run-scoped ULog found for $CASE_ID" >&2
  exit 1
fi
cp "$ULOG" "$CASE_DIR/raw.ulg"
printf '%s\n' "$ULOG" > "$CASE_DIR/ulog_source_path.txt"
sha256sum "$CASE_DIR/raw.ulg" > "$CASE_DIR/raw.ulg.sha256"

receipt_args=()
if [ "$MOTOR" -ge 0 ]; then
  if [ ! -s "$RECEIPT" ]; then
    echo "Fault case $CASE_ID has no simulator-side HRT receipt" >&2
    exit 1
  fi
  receipt_args=(--fault-receipt "$RECEIPT")
fi
python "$REPO_ROOT/scripts/px4_ulog_to_ornik_trace.py" \
  "$CASE_DIR/raw.ulg" \
  --mission-metadata "$CASE_DIR/mission_metadata.json" \
  "${receipt_args[@]}" \
  --rate-hz 50 \
  --evaluation-horizon-s 8 \
  --out "$CASE_DIR/trace.csv" \
  --summary-out "$CASE_DIR/trace_summary.json"
