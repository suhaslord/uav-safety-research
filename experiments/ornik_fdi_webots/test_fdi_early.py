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

if __name__=='__main__':
    unittest.main()
