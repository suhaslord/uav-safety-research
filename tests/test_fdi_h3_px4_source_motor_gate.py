"""Synthetic source-layout changes must not pass H3 static motor mapping.

No simulator, aircraft or motor actuation is involved in these tests.
"""
import tempfile
import unittest
from pathlib import Path

from scripts.fdi_h3_px4_source_motor_gate import EXPECTED, audit_files, audit_xml


def fixture():
    plugins = []
    rotors = []
    for index, (x, y, spin) in EXPECTED.items():
        plugins.append(
            f'<plugin filename="gz-sim-multicopter-motor-model-system" '
            f'name="gz::sim::systems::MulticopterMotorModel">'
            f'<motorNumber>{index}</motorNumber>'
            f'<linkName>rotor_{index}</linkName>'
            f'<jointName>rotor_{index}_joint</jointName>'
            f'<turningDirection>{spin}</turningDirection>'
            f'<commandSubTopic>command/motor_speed</commandSubTopic>'
            f'<motorType>velocity</motorType></plugin>'
        )
        rotors.append(
            f'<link name="rotor_{index}"><pose>{x} {y} 0.06 0 0 0</pose></link>'
            f'<joint name="rotor_{index}_joint" type="revolute">'
            f'<parent>base_link</parent><child>rotor_{index}</child></joint>'
        )
    motor = ('<sdf><model name="x500"><include><uri>model://x500_base'
             '</uri></include>' + ''.join(plugins) + '</model></sdf>')
    base = '<sdf><model name="x500_base">' + ''.join(rotors) + '</model></sdf>'
    return motor, base


class SourceMotorMapTests(unittest.TestCase):
    def test_frozen_source_layout_passes_only_static_gate(self):
        motor, base = fixture()
        result = audit_xml(motor, base)
        self.assertEqual(result["status"], "STATIC_SOURCE_MAP_VERIFIED")
        self.assertEqual([entry["source_motor_index"] for entry in result["motors"]],
                         [0, 1, 2, 3])
        self.assertFalse(result["physical_motor_map_verified"])
        self.assertFalse(result["applied_actuation_verified"])
        self.assertFalse(result["can_claim_h3_results"])

    def test_duplicate_motor_number_rejected(self):
        motor, base = fixture()
        motor = motor.replace("<motorNumber>3</motorNumber>",
                              "<motorNumber>0</motorNumber>")
        self.assertEqual(audit_xml(motor, base)["status"], "REJECTED")

    def test_swapped_plugin_joint_rejected(self):
        motor, base = fixture()
        motor = motor.replace("<jointName>rotor_0_joint</jointName>",
                              "<jointName>rotor_1_joint</jointName>")
        self.assertIn("joint mismatch", str(audit_xml(motor, base)["errors"]))

    def test_changed_rotor_position_rejected(self):
        motor, base = fixture()
        base = base.replace("<pose>0.174 -0.174 0.06", "<pose>-0.174 -0.174 0.06")
        self.assertIn("position differs", str(audit_xml(motor, base)["errors"]))

    def test_wrong_spin_rejected(self):
        motor, base = fixture()
        motor = motor.replace("<turningDirection>ccw</turningDirection>",
                              "<turningDirection>cw</turningDirection>", 1)
        self.assertIn("spin direction", str(audit_xml(motor, base)["errors"]))

    def test_wrong_command_topic_rejected(self):
        motor, base = fixture()
        motor = motor.replace("<commandSubTopic>command/motor_speed</commandSubTopic>",
                              "<commandSubTopic>other/topic</commandSubTopic>", 1)
        self.assertIn("command topic", str(audit_xml(motor, base)["errors"]))

    def test_missing_joint_rejected(self):
        motor, base = fixture()
        base = base.replace('name="rotor_2_joint"', 'name="wrong_joint"')
        self.assertIn("link/joint missing", str(audit_xml(motor, base)["errors"]))

    def test_invalid_xml_fails_closed(self):
        self.assertEqual(audit_xml("<sdf>", "<sdf/>")["status"], "REJECTED")

    def test_nonfinite_pose_rejected(self):
        motor, base = fixture()
        base = base.replace("<pose>0.174 -0.174", "<pose>nan -0.174")
        self.assertIn("invalid link pose", str(audit_xml(motor, base)["errors"]))

    def test_file_audit_records_both_input_hashes(self):
        motor, base = fixture()
        with tempfile.TemporaryDirectory() as directory:
            a, b = Path(directory) / "motor.sdf", Path(directory) / "base.sdf"
            a.write_text(motor)
            b.write_text(base)
            result = audit_files(a, b)
            self.assertEqual(len(result["model_sdf_sha256"]), 64)
            self.assertEqual(len(result["base_sdf_sha256"]), 64)
            self.assertEqual(result["status"], "STATIC_SOURCE_MAP_VERIFIED")


if __name__ == "__main__":
    unittest.main()
