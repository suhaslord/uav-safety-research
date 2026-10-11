"""H2 independent artifact auditor regression tests, entirely synthetic.

Tests intentionally avoid the 144-trajectory protected Webots evaluation.
"""
import hashlib
import io
import json
import random
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts import audit_fdi_h2_artifact as h2


def sensor(t, p=0, q=0, z=1):
    return {"time_s":str(t),"gyro_p_rps":str(p),"gyro_q_rps":str(q),"z_m":str(z)}


class H2ArtifactAuditUnitTests(unittest.TestCase):
    def test_exact_registered_matrix(self):
        items=list(h2.cases())
        self.assertEqual(len(items),144)
        self.assertEqual(len({h2.name(x) for x in items}),144)
        self.assertEqual(len(h2.SEEDS),8)
        self.assertEqual(len(set(h2.SEEDS)),8)
        self.assertEqual(len([x for x in items if x[2]==0]),16)

    def test_replay_all_motor_quadrants_and_times(self):
        for onset in h2.ONSETS:
            for motor,p,q in [(1,3,1),(2,3,-1),(3,-3,-1),(4,-3,1)]:
                with self.subTest(onset=onset,motor=motor):
                    case=(89,onset,motor,0.)
                    rows=[sensor(onset-.6)]+[sensor(onset+.032*i,p,q) for i in (1,2,3)]
                    pred,t,z,pre=h2.replay(rows,case,0.)
                    self.assertEqual(pred,motor)
                    self.assertAlmostEqual(t,onset+.096)
                    self.assertEqual(z,1.)
                    self.assertFalse(pre)

    def test_streak_reset_and_censor(self):
        case=(89,9.,1,.5)
        self.assertEqual(h2.replay([sensor(9.01,3,1),sensor(9.042,3,1),
                                     sensor(9.074),sensor(9.106,3,1),
                                     sensor(9.138,3,1)],case,0.)[0],0)
        self.assertEqual(h2.replay([sensor(9.01,3,1,z=.4),sensor(9.042,3,1),
                                     sensor(9.074,3,1),sensor(9.106,3,1)],case,0.)[0],0)
        self.assertEqual(h2.replay([sensor(9.71+i*.032,3,1) for i in range(4)],case,0.)[0],0)

    def test_preonset_is_error_even_when_class_correct(self):
        predicted,time,altitude,pre=h2.replay([sensor(8.6+i*.032,3,1) for i in range(3)],
                                                (89,9.,1,0.),0.)
        self.assertEqual(predicted,1)
        self.assertTrue(pre)
        rows=[dict(motor=i,prediction=i,pre_onset=(i==1),
                   alert_time_s=(time if i==1 else 9.272 if i else None),onset=9.)
              for i in range(5)]
        self.assertAlmostEqual(h2.rows_metrics(rows)["temporal_valid_balanced_accuracy"],.8)

    def test_replay_gaussian_noise_is_repeatable(self):
        case=(89,13.,2,.5)
        rows=[sensor(12+i*.032,2.3,-.9) for i in range(38)]
        self.assertEqual(h2.replay(rows,case,.2),h2.replay(rows,case,.2))
        self.assertEqual(h2.seeded_rng(*case,.2).gauss(0,.2),
                         h2.seeded_rng(*case,.2).gauss(0,.2))

    def test_numeric_fields_reject_nonfinite(self):
        fields={name:"0" for name in h2.FIELDS}
        for name in h2.FIELDS:
            with self.subTest(name=name):
                broken=dict(fields);broken[name]="nan"
                with self.assertRaisesRegex(ValueError,"nonfinite"):
                    h2.float_checked(broken,name,"synthetic.csv")

    def test_duplicate_zip_members_fail_even_if_set_looks_valid(self):
        names=["report/h2_results.json","raw/seed89.csv","raw/seed89.csv"]
        with self.assertRaisesRegex(ValueError,"Duplicate ZIP members"):
            h2.validate_archive_members(names)

    def test_decision_and_trace_headers_fail_closed(self):
        h2.validate_csv_headers(h2.DECISION_HEADERS,h2.DECISION_HEADERS,"scores")
        h2.validate_csv_headers(h2.TRACE_HEADERS,h2.TRACE_HEADERS,"trace")
        for headers,expected in [
            (h2.DECISION_HEADERS[:-1],h2.DECISION_HEADERS),
            (h2.TRACE_HEADERS+("seed",),h2.TRACE_HEADERS),
            (list(h2.TRACE_HEADERS)[::-1],h2.TRACE_HEADERS),
        ]:
            with self.subTest(headers=headers):
                with self.assertRaisesRegex(ValueError,"CSV schema"):
                    h2.validate_csv_headers(headers,expected,"synthetic")

    def test_corrupted_preonset_boolean_must_not_be_silently_false(self):
        self.assertTrue(h2.read_bool_exact("True","synthetic"))
        self.assertFalse(h2.read_bool_exact("False","synthetic"))
        for invalid in ("", "false", "0", "N/A", None):
            with self.subTest(value=invalid):
                with self.assertRaisesRegex(ValueError,"pre_onset"):
                    h2.read_bool_exact(invalid,"synthetic")

    def test_external_sha256_detects_altered_evidence_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"synthetic.zip"
            path.write_bytes(b"synthetic and explicitly not real flight evidence")
            sha=hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertTrue(h2.verify_archive_sha256(path,sha))
            with self.assertRaisesRegex(ValueError,"64 hexadecimal"):
                h2.verify_archive_sha256(path,"not a hash")
            path.write_bytes(path.read_bytes()+b"changed")
            with self.assertRaisesRegex(ValueError,"differs"):
                h2.verify_archive_sha256(path,sha)

    def test_partial_artifact_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"partial.zip"
            with zipfile.ZipFile(path,"w") as fh:
                fh.writestr("report/h2_results.json",json.dumps({"physical_traces":144}))
                fh.writestr("report/per_case_decisions.csv","seed,onset,motor\n")
            with self.assertRaisesRegex(ValueError,"Missing required"):
                h2.audit(path)

    def test_published_metric_tampering_is_rejected(self):
        rows=[dict(motor=m,prediction=m,pre_onset=False,alert_time_s=9.272 if m else None,onset=9.)
              for m in range(5)]
        published=h2.rows_metrics(rows)
        published["temporal_valid_balanced_accuracy"]=.8
        with self.assertRaisesRegex(ValueError,"balanced_accuracy"):
            h2.check_metric(h2.rows_metrics(rows),published,"synthetic")


if __name__=="__main__":
    unittest.main()
