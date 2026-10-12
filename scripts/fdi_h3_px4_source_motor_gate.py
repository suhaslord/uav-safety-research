#!/usr/bin/env python3
"""Read-only, pinned-source structure check for the PX4/Gazebo x500 motor path.

This inspects model XML only. Static index/joint correspondence is NOT
proof of applied rotor speed, actual thrust, gyro-axis parity, an injected
motor fault, independent dynamics admission, or H3 performance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from xml.etree import ElementTree as ET

# Frozen *Gazebo source* coordinates, not translated H1 motor-class labels.
EXPECTED = {
    0: (0.174, -0.174, "ccw"),
    1: (-0.174, 0.174, "ccw"),
    2: (0.174, 0.174, "cw"),
    3: (-0.174, -0.174, "cw"),
}
MOTOR_PLUGIN = "gz::sim::systems::MulticopterMotorModel"


def audit_xml(motor_xml: str, base_xml: str) -> dict:
    errors: list[str] = []
    entries: list[dict] = []

    def check(condition: bool, message: str) -> None:
        if not condition:
            errors.append(message)

    try:
        motor_root = ET.fromstring(motor_xml)
        base_root = ET.fromstring(base_xml)
    except ET.ParseError as exc:
        return {"study": "FDI-H3", "status": "REJECTED",
                "errors": [f"malformed model XML: {exc}"],
                "motors": [], "can_claim_h3_results": False,
                "physical_motor_map_verified": False,
                "applied_actuation_verified": False}

    model = motor_root.find("./model")
    base = base_root.find("./model")
    if model is None or base is None:
        errors.append("missing SDF model")
        return _report(errors, entries)
    check(model.get("name") == "x500", "expected x500 motor model")
    check(base.get("name") == "x500_base", "expected x500_base structural model")
    includes = [node.findtext("uri") for node in model.findall("./include")]
    check(includes.count("model://x500_base") == 1,
          "x500 must include exactly one x500_base model")

    plugins = [node for node in model.findall("./plugin")
               if node.get("name") == MOTOR_PLUGIN]
    check(len(plugins) == 4, "exactly four Gazebo motor plugins required")
    links = {link.get("name"): link for link in base.findall("./link")}
    joints = {joint.get("name"): joint for joint in base.findall("./joint")}
    seen_indices: set[int] = set()

    for plugin in plugins:
        try:
            index = int(plugin.findtext("motorNumber", ""))
        except ValueError:
            errors.append("motorNumber must be an integer")
            continue
        if index in seen_indices:
            errors.append(f"duplicate motor index {index}")
            continue
        seen_indices.add(index)
        if index not in EXPECTED:
            errors.append(f"unexpected motor index {index}")
            continue

        x_expected, y_expected, direction_expected = EXPECTED[index]
        link_name = f"rotor_{index}"
        joint_name = f"{link_name}_joint"
        check(plugin.get("filename") == "gz-sim-multicopter-motor-model-system",
              f"motor {index} plugin filename changed")
        check(plugin.findtext("linkName") == link_name,
              f"motor {index} plugin rotor link mismatch")
        check(plugin.findtext("jointName") == joint_name,
              f"motor {index} plugin joint mismatch")
        check(plugin.findtext("turningDirection") == direction_expected,
              f"motor {index} spin direction changed")
        check(plugin.findtext("commandSubTopic") == "command/motor_speed",
              f"motor {index} command topic changed")
        check(plugin.findtext("motorType") == "velocity",
              f"motor {index} motor type changed")

        link = links.get(link_name)
        joint = joints.get(joint_name)
        if link is None or joint is None:
            errors.append(f"motor {index} link/joint missing in x500_base")
            continue
        check(joint.get("type") == "revolute" and
              joint.findtext("parent") == "base_link" and
              joint.findtext("child") == link_name,
              f"motor {index} joint parent/child/type changed")
        try:
            pose = [float(value) for value in (link.findtext("pose") or "").split()]
            if len(pose) != 6 or not all(math.isfinite(v) for v in pose):
                raise ValueError("pose must contain six finite numbers")
        except ValueError:
            errors.append(f"motor {index} has invalid link pose")
            continue
        check(math.isclose(pose[0], x_expected, rel_tol=0, abs_tol=1e-9) and
              math.isclose(pose[1], y_expected, rel_tol=0, abs_tol=1e-9),
              f"motor {index} position differs from pinned x500 source")
        entries.append({"source_motor_index": index, "rotor_link": link_name,
                        "joint": joint_name, "spin": direction_expected,
                        "source_xy_m": [pose[0], pose[1]],
                        "command_topic": "command/motor_speed"})

    check(seen_indices == set(EXPECTED), "source motor indices must be 0, 1, 2, 3")
    entries.sort(key=lambda entry: entry["source_motor_index"])
    return _report(errors, entries)


def _report(errors: list[str], entries: list[dict]) -> dict:
    return {
        "study": "FDI-H3",
        "status": "STATIC_SOURCE_MAP_VERIFIED" if not errors else "REJECTED",
        "errors": errors,
        "motors": entries,
        "can_claim_h3_results": False,
        "physical_motor_map_verified": False,
        "applied_actuation_verified": False,
        "fault_injection_verified": False,
        "note": "Only pinned Gazebo model source structure was checked; no runtime "
                "measurement, actuator fault or H1 mapping was verified.",
    }


def audit_files(motor_path: Path, base_path: Path) -> dict:
    motor_bytes, base_bytes = motor_path.read_bytes(), base_path.read_bytes()
    result = audit_xml(motor_bytes.decode("utf-8"), base_bytes.decode("utf-8"))
    result["model_sdf_sha256"] = hashlib.sha256(motor_bytes).hexdigest()
    result["base_sdf_sha256"] = hashlib.sha256(base_bytes).hexdigest()
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model-sdf", type=Path, required=True)
    ap.add_argument("--base-sdf", type=Path, required=True)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    result = audit_files(args.model_sdf, args.base_sdf)
    body = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    print(body, end="")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(body, encoding="utf-8")
    raise SystemExit(0 if result["status"] == "STATIC_SOURCE_MAP_VERIFIED" else 2)


if __name__ == "__main__":
    main()
