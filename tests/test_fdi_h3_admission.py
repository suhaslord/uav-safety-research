"""Prospective H3 source admission checks; no protected dataset or simulator."""
import json
import tempfile
import unittest
from pathlib import Path
from scripts.fdi_h3_admission import PREVIOUSLY_USED, evaluate_file, validate


def candidate():
    return {
        "study_id": "FDI-H3",
        "engine": {
            "implementation": "independent_simulation_candidate",
            "dynamics_family": "external-engine-not-webots",
            "source_url": "https://example.org/independent-source",
            "commit_sha": "a" * 40,
            "runtime_digest": "sha256:" + "b" * 64,
            "independence_evidence_url": "https://example.org/analysis",
        },
        "interface": {
            "gyro_units": "rad/s",
            "gyro_axes": ["body_roll_rate_p", "body_pitch_rate_q"],
            "motor_order": [1, 2, 3, 4],
            "motor_quadrant_map": {"++": 1, "+-": 2, "--": 3, "-+": 4},
            "sample_period_s": .032,
            "altitude_reference": "world vertical from datum",
            "contact_indicator": "simulated touchdown event",
        },
        "method": {
            "threshold_p_radps": 2.0,
            "threshold_q_radps": .75,
            "consecutive_samples": 3,
            "speed_retentions": [0.0, .5, .8],
            "injection_site": "simulated_actuator_model",
            "online_gyro_noise": True,
            "online_gyro_noise_spec_url": "https://example.org/noise",
        },
        "splits": {
            "development_seeds": [130, 131],
            "protected_seeds": list(range(200, 212)),
        },
        "development_protocol_url": "https://example.org/dev",
        "protected_protocol_url": "https://example.org/protected",
        "manifest_archive_url": "https://example.org/archive",
    }


class FDIH3AdmissionTests(unittest.TestCase):
    def test_complete_form_is_only_review_ready_not_admitted(self):
        self.assertEqual(validate(candidate()), [])
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "manifest.json"
            path.write_text(json.dumps(candidate()), encoding="utf-8")
            result = evaluate_file(path)
            self.assertEqual(result["status"], "READY_FOR_INDEPENDENT_SOURCE_REVIEW")
            self.assertFalse(result["can_claim_h3_results"])
            self.assertFalse(result["independent_dynamics_verified"])
            self.assertEqual(len(result["manifest_sha256"]), 64)

    def test_reject_same_webots_engine_and_reused_seeds(self):
        doc = candidate()
        doc["engine"]["dynamics_family"] = "bitcraze-webots"
        doc["splits"]["protected_seeds"][0] = 89
        findings = validate(doc)
        self.assertTrue(any("independent dynamics" in x for x in findings))
        self.assertTrue(any("known H1/H2" in x for x in findings))

    def test_reject_threshold_tuning_and_offline_noise_shortcut(self):
        doc = candidate()
        doc["method"]["threshold_p_radps"] = 1.5
        doc["method"]["online_gyro_noise"] = False
        findings = validate(doc)
        self.assertTrue(any("threshold" in x for x in findings))
        self.assertTrue(any("online" in x for x in findings))

    def test_reject_data_leakage_and_small_holdout(self):
        doc = candidate()
        doc["splits"]["protected_seeds"] = [130, 133, 134]
        problems = validate(doc)
        self.assertTrue(any("leakage" in x for x in problems))
        self.assertTrue(any("12" in x for x in problems))

    def test_malformed_seed_lists_rejected_without_type_error(self):
        for invalid in (["oops", {"fake": 1}], [True, 203, 204], [201.5, 202], [[210], 211], {"seeds": [210]}, None):
            with self.subTest(invalid=invalid):
                doc = candidate()
                doc["splits"]["protected_seeds"] = invalid
                findings = validate(doc)
                self.assertTrue(any("protected seeds must" in x for x in findings))

    def test_malformed_development_split_does_not_skip_holdout_check(self):
        doc = candidate()
        doc["splits"]["development_seeds"] = [[], 132]
        doc["splits"]["protected_seeds"] = [200] * 12
        findings = validate(doc)
        self.assertTrue(any("development seeds must" in x for x in findings))
        self.assertTrue(any("duplicates" in x for x in findings))

    def test_empty_development_and_invalid_sample_period_rejected(self):
        doc = candidate()
        doc["splits"]["development_seeds"] = []
        doc["interface"]["sample_period_s"] = float("nan")
        findings = validate(doc)
        self.assertTrue(any("nonempty development" in x for x in findings))
        self.assertTrue(any("finite sample period" in x for x in findings))

    def test_engine_identity_type_validation(self):
        doc = candidate()
        doc["engine"]["dynamics_family"] = ["different", "words"]
        self.assertTrue(any("independent dynamics" in x for x in validate(doc)))

    def test_all_h1_h2_seeds_are_protected_from_reuse(self):
        doc = candidate()
        for used in PREVIOUSLY_USED:
            with self.subTest(seed=used):
                doc["splits"]["development_seeds"] = [used]
                self.assertTrue(any("known H1/H2" in s for s in validate(doc)))

if __name__ == "__main__":
    unittest.main()
