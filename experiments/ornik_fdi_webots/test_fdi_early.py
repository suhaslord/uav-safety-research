"""Local checks for the pre-contact Webots FDI experiment; require no simulator."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluate_fdi_early import early_decision, metrics, bootstrap_test, TEST_SEEDS

def row(t,p=0,q=0,z=1):
    return {'time_s':str(t),'gyro_p_rps':str(p),
            'gyro_q_rps':str(q),'z_m':str(z)}

class EarlyFDIValidation(unittest.TestCase):
    def test_quadrants_and_causal_persistence(self):
        patterns={1:(3,2),2:(3,-2),3:(-3,-2),4:(-3,2)}
        for expected,(p,q) in patterns.items():
            with self.subTest(motor=expected):
                samples=[row(9.5),row(10.02,p,q),row(10.052,p,q),row(10.084,p,q)]
                res=early_decision(samples)
                self.assertEqual(res['prediction'],expected)
                self.assertEqual(res['alert_time_s'],10.084)
    def test_pre_onset_alert_is_false_alarm(self):
        res=early_decision([row(9,4,2),row(9.032,4,2),row(9.064,4,2)])
        self.assertEqual(res['prediction'],1)
        self.assertTrue(res['false_alert_before_onset'])
    def test_early_impact_censors_late_alert(self):
        res=early_decision([row(10.02,5,2,z=.49),row(10.05,5,2)])
        self.assertEqual(res['prediction'],0)
    def test_last_time_censors_unrealistic_late_gyro(self):
        res=early_decision([row(10.8,10000,5000)]*5)
        self.assertEqual(res['prediction'],0)
    def test_seed_level_confidence_interval(self):
        rows=[{'seed':s,'motor':m,'prediction':m,'alert_time_s':10.3 if m else None}
              for s in TEST_SEEDS for m in range(5)]
        self.assertEqual(metrics(rows)['balanced_accuracy'],1.0)
        self.assertEqual(bootstrap_test(rows)['percentile_95_interval'],[1.0,1.0])
        for r in rows: r['prediction']=0
        self.assertEqual(metrics(rows)['balanced_accuracy'],0.2)
        self.assertEqual(bootstrap_test(rows)['percentile_95_interval'],[0.2,0.2])

    def test_detection_is_not_equivalent_to_correct_isolation(self):
        # Two paired seeds with imperfect outcomes. Wrong motor labels
        # count as detections but NOT as correct fault isolation.
        records = []
        for seed in (901, 903):
            for motor in range(5):
                predicted = motor
                if motor == 1:
                    predicted = 0             # missed fault
                elif motor == 2:
                    predicted = 3             # detected, wrongly isolated
                elif motor == 0 and seed == 903:
                    predicted = 1             # healthy false alarm
                records.append(dict(
                    seed=seed, motor=motor, prediction=predicted,
                    alert_time_s=10.25 if predicted and motor else None))
        results = metrics(records)
        self.assertEqual(results['balanced_accuracy'], 0.5)
        self.assertEqual(results['healthy_false_alarm_rate'], 0.5)
        self.assertEqual(results['fault_detection_rate'], 0.75)
        self.assertEqual(results['correct_fault_isolation_rate'], 0.5)
        self.assertEqual(results['confusion_matrix_rows_true_cols_predicted'][2][3], 2)

    def test_seed_cluster_bootstrap_reflects_seed_failure(self):
        records = [
            {'seed': seed, 'motor': motor,
             'prediction': (0 if seed == TEST_SEEDS[-1] else motor),
             'alert_time_s': 10.25 if motor and seed != TEST_SEEDS[-1] else None}
            for seed in TEST_SEEDS for motor in range(5)]
        lo, hi = bootstrap_test(records)['percentile_95_interval']
        self.assertLess(lo, hi)
        self.assertGreaterEqual(lo, 0.2)
        self.assertLessEqual(hi, 1.0)

if __name__=='__main__':
    unittest.main()
