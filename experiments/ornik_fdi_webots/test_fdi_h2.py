"""H2 preregistered analytic invariants; no Webots run or protected traces required."""
import random
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from evaluate_fdi_h2 import (
    SEEDS, ONSETS, RETENTIONS, NOISE_SIGMAS, scenario_cases,
    classify, measure, subset, bootstrap, noise_rng, file_name,
)

def point(t,p=0,q=0,z=1):
    return {"time_s":str(t),"gyro_p_rps":str(p),"gyro_q_rps":str(q),"z_m":str(z)}

class ProspectiveH2Tests(unittest.TestCase):
    def test_frozen_inputs_and_split_size(self):
        cases=list(scenario_cases())
        self.assertEqual(len(cases),144)
        self.assertEqual(len({file_name(*args) for args in cases}),144)
        self.assertEqual((ONSETS,RETENTIONS,NOISE_SIGMAS),((9.0,13.0),(0.0,0.5),(0.0,0.2,1.0)))
        self.assertEqual(len(SEEDS),8)
        self.assertTrue(set(SEEDS).isdisjoint({11,23,29,31,41,47,53,59,61,67,71,73,79,83}))

    def test_unchanged_quadrant_detector_varied_fault_time(self):
        signals={1:(3,1),2:(3,-1),3:(-3,-1),4:(-3,1)}
        for onset in ONSETS:
            for target,(p,q) in signals.items():
                with self.subTest(onset=onset,motor=target):
                    rows=[point(onset-0.5)] + [point(onset+.032*i,p,q) for i in range(1,4)]
                    answer=classify(rows,onset,0,random.Random(1))
                    self.assertEqual(answer["prediction"],target)
                    self.assertFalse(answer["pre_onset"])
                    self.assertAlmostEqual(answer["alert_time_s"],onset+.096)

    def test_temporal_error_not_credited(self):
        onset=13.0
        early=classify([point(12.0+i*.032,3,1) for i in range(4)],onset,0,random.Random(1))
        self.assertTrue(early["pre_onset"])
        records=[{"motor":m,"prediction":(1 if m==1 else m),
                  "pre_onset":(early["pre_onset"] if m==1 else False),
                  "alert_time_s":early["alert_time_s"] if m==1 else (onset+.2 if m>0 else None),
                  "onset":onset} for m in range(5)]
        scored=measure(records)
        self.assertAlmostEqual(scored["temporal_valid_balanced_accuracy"],.8)
        self.assertEqual(scored["premature_alert_count"],1)

    def test_early_ground_contact_censors(self):
        rows=[point(9.02,3,1,z=.4),point(9.052,3,1),point(9.084,3,1)]
        self.assertEqual(classify(rows,9.,0.,random.Random(0))["prediction"],0)

    def test_random_gyro_noise_reproducibility(self):
        for sigma in (.2,1.):
            rng1=noise_rng(89,9.,1,.5,sigma)
            rng2=noise_rng(89,9.,1,.5,sigma)
            self.assertEqual([rng1.gauss(0,sigma) for _ in range(12)],
                             [rng2.gauss(0,sigma) for _ in range(12)])

    def test_paired_seed_interval_and_baseline(self):
        records=[]
        for seed in SEEDS:
            for onset in ONSETS:
                records.append(dict(seed=seed,onset=onset,motor=0,retention=1.,
                                    sensor_noise_sigma_radps=0.,prediction=0,
                                    pre_onset=False,alert_time_s=None))
                for keep in RETENTIONS:
                    for motor in range(1,5):
                        records.append(dict(seed=seed,onset=onset,motor=motor,retention=keep,
                                            sensor_noise_sigma_radps=0.,prediction=motor,
                                            pre_onset=False,alert_time_s=onset+.272))
        for keep in RETENTIONS:
            selected=subset(records,keep,noise=0.)
            self.assertEqual(len(selected),80)
            self.assertEqual(measure(selected)["temporal_valid_balanced_accuracy"],1.0)
            self.assertEqual(bootstrap(selected)["percentile_95_interval"],[1.,1.])
            for r in selected:
                r["prediction"]=0
            self.assertEqual(measure(selected)["temporal_valid_balanced_accuracy"],.2)

if __name__=="__main__":
    unittest.main()
