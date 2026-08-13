from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

INCLUDE_ANCHOR = '#include "GZMixingInterfaceESC.hpp"\n'
LOOP_ANCHOR = '''\t\tfor (unsigned i = 0; i < active_output_count; i++) {\n\t\t\trotor_velocity_message.set_velocity(i, outputs[i]);\n\t\t}\n'''

INCLUDES = '''#include "GZMixingInterfaceESC.hpp"\n\n#include <algorithm>\n#include <cmath>\n#include <cstdlib>\n#include <fstream>\n#include <string>\n'''

REPLACEMENT = '''\t\tstatic const int aegis_fault_motor = []() {\n\t\t\tconst char *value = std::getenv("AEGIS_FAULT_MOTOR");\n\t\t\treturn value ? std::atoi(value) : -1;\n\t\t}();\n\t\tstatic const double aegis_fault_effectiveness = []() {\n\t\t\tconst char *value = std::getenv("AEGIS_FAULT_EFFECTIVENESS");\n\t\t\treturn std::clamp(value ? std::atof(value) : 1.0, 0.0, 1.0);\n\t\t}();\n\t\tstatic const double aegis_model_thrust_scale = []() {\n\t\t\tconst char *value = std::getenv("AEGIS_MODEL_THRUST_SCALE");\n\t\t\treturn std::clamp(value ? std::atof(value) : 1.0, 0.25, 2.0);\n\t\t}();\n\t\tstatic const std::string aegis_trigger_path = []() {\n\t\t\tconst char *value = std::getenv("AEGIS_FAULT_TRIGGER_FILE");\n\t\t\treturn std::string(value ? value : "/tmp/aegis_ornik_fault.trigger");\n\t\t}();\n\t\tstatic const std::string aegis_receipt_path = []() {\n\t\t\tconst char *value = std::getenv("AEGIS_FAULT_RECEIPT_FILE");\n\t\t\treturn std::string(value ? value : "/tmp/aegis_ornik_fault_receipt.csv");\n\t\t}();\n\t\tstatic bool aegis_receipt_written = false;\n\n\t\tconst bool aegis_fault_active = aegis_fault_motor >= 0 && std::ifstream(aegis_trigger_path).good();\n\t\tconst double global_speed_scale = std::sqrt(aegis_model_thrust_scale);\n\t\tconst double fault_speed_scale = std::sqrt(aegis_fault_effectiveness);\n\n\t\tfor (unsigned i = 0; i < active_output_count; i++) {\n\t\t\tdouble simulated_speed = static_cast<double>(outputs[i]) * global_speed_scale;\n\n\t\t\tif (aegis_fault_active && static_cast<int>(i) == aegis_fault_motor) {\n\t\t\t\tsimulated_speed *= fault_speed_scale;\n\n\t\t\t\tif (!aegis_receipt_written) {\n\t\t\t\t\tstd::ofstream receipt(aegis_receipt_path, std::ios::out | std::ios::trunc);\n\t\t\t\t\treceipt << "fault_onset_hrt_us,motor,effectiveness,speed_scale,model_thrust_scale\\n";\n\t\t\t\t\treceipt << hrt_absolute_time() << "," << aegis_fault_motor << ","\n\t\t\t\t\t\t<< aegis_fault_effectiveness << "," << fault_speed_scale << ","\n\t\t\t\t\t\t<< aegis_model_thrust_scale << "\\n";\n\t\t\t\t\treceipt.close();\n\t\t\t\t\taegis_receipt_written = true;\n\t\t\t\t}\n\t\t\t}\n\n\t\t\trotor_velocity_message.set_velocity(i, simulated_speed);\n\t\t}\n'''


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def patch_text(text: str) -> str:
    if 'AEGIS_FAULT_EFFECTIVENESS' in text:
        return text
    if INCLUDE_ANCHOR not in text:
        raise RuntimeError('PX4 include anchor not found; refusing ambiguous patch')
    if LOOP_ANCHOR not in text:
        raise RuntimeError('PX4 updateOutputs anchor not found; refusing ambiguous patch')
    text = text.replace(INCLUDE_ANCHOR, INCLUDES, 1)
    text = text.replace(LOOP_ANCHOR, REPLACEMENT, 1)
    return text


def main() -> None:
    p = argparse.ArgumentParser(description='Patch PX4 v1.17 Gazebo ESC bridge with AegisLand simulation-only actuator effectiveness injection.')
    p.add_argument('source', type=Path)
    p.add_argument('--receipt', type=Path, required=True)
    args = p.parse_args()
    original = args.source.read_bytes()
    patched_text = patch_text(original.decode('utf-8'))
    args.source.write_text(patched_text, encoding='utf-8')
    patched = args.source.read_bytes()
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(
        f'original_sha256={sha256_bytes(original)}\npatched_sha256={sha256_bytes(patched)}\nsource={args.source}\n',
        encoding='utf-8',
    )
    print(args.receipt.read_text())


if __name__ == '__main__':
    main()
