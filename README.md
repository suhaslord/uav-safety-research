# AegisLand

A simulation study of one question:

> **When UAV landing perception is confidently wrong, can an independent estimate catch the error without causing too many unnecessary interventions?**

I built AegisLand to test that question with synthetic landing experiments and PX4/Gazebo camera evidence. The project is **simulation-only** and is not flight-control software.

[Research cockpit](https://aegisland-research-cockpit.vercel.app/) · [Phase 10R result](docs/phase10r_frozen_holdout_result.md) · [Phase 10R protocol](docs/phase10r_frozen_holdout_protocol.md)

## What I did

- Built the simulation and evaluation pipeline used to compare perception/supervision variants.
- Added independent/redundant state estimates to test whether disagreement can reveal persistent visual bias.
- Added confidence/abstention logic and measured the safety cost of refusing uncertain estimates.
- Moved from synthetic perception failures to PX4/Gazebo camera evidence.
- Used frozen evaluation sets and kept failed gates/results instead of retuning after seeing the holdout.
- Tracked point error, tail error, missed observations, false positives, and uncertainty coverage.

## Current result

Phase 10R was frozen at `e1d566f8baa47bf10f9bdf39dd5988724208be80` and evaluated once on a new holdout containing **12 trajectories, 3 appearance conditions, 36 sequences, and 1,440 truth-visible frames**.

The result was **mixed and failed the preregistered all-gates rule**.

| Check | Result |
|---|---:|
| Clean lateral / altitude MAE vs Phase 9 | `0.704× / 0.417×` — pass |
| Ambiguous lateral MAE improvement | `79.2%` — pass |
| Ambiguous altitude MAE improvement | `73.7%` — pass |
| Ambiguous lateral p95 improvement | `-1.1%` — fail |
| Ambiguous altitude p95 improvement | `7.3%` — fail |
| Truth-visible miss rate | `20.0%` — fail |
| False-positive rate | `0.0%` — pass |
| 95% uncertainty coverage | `84.3% lateral / 79.7% altitude` — fail |

### What that means

The method reduced **average** error on ambiguous views, but it did not solve the difficult error tail. It also missed too many truth-visible frames, and uncertainty that looked calibrated during development became overconfident after the appearance/geometry shift.

So the strongest conclusion I can support is:

> **Good in-domain calibration did not automatically survive distribution shift.**

That is why I am not calling Phase 10R a safety success.

## Earlier experiments

### Phase 10

On a Gazebo-camera holdout, the temporal estimator did **not** improve point error over Phase 9: both produced `2.77 cm` lateral and `1.57 cm` altitude MAE on paired usable observations.

What did improve was uncertainty calibration:

- median `|residual| / sigma`: `13.17 → 0.65` lateral and `5.11 → 0.52` altitude;
- 2-sigma coverage: `93%` lateral and `100%` altitude.

The point-error gate failed, so I froze the mixed result instead of tuning on the holdout.

### Phase 6B

In the earlier synthetic benchmark:

| Architecture | Success | Unsafe |
|---|---:|---:|
| Image-only temporal | `57%` | `43%` |
| Phase 6 Aegis | `94%` | `6%` |
| Phase 6B selective | `99%` | `1%` |

The selective version also kept a **3% timeout cost** in low light. These numbers apply only to that synthetic benchmark.

### V3

A separate abstract redundant-perception experiment produced:

| Architecture | Unsafe | Success |
|---|---:|---:|
| Baseline | `84.2%` | `15.8%` |
| Temporal smoothing | `84.0%` | `16.0%` |
| Redundant estimate | `2.4%` | `97.6%` |

My interpretation: smoothing a single biased stream did not reveal the bias, while an independent error source could expose it in this benchmark.

## What failed / limitations

- No hardware-camera or physical-flight validation.
- Phase 10R miss rate was `20%`, above the preregistered `10%` limit.
- Phase 10R p95 gates failed even though mean error improved.
- Phase 10R uncertainty coverage fell to `84.3% / 79.7%` under shift.
- The Phase 10 holdout was small: 20 truth-visible frames and 15 paired observations.
- A short PX4/Gazebo trace in Phase 8 showed a **diagnostic mismatch**, not a validation pass.
- Passing software tests does not imply flight safety.

## Why the evaluation is frozen

I separate development data from protected evaluation data so I cannot keep rerunning or retuning until a result looks good. Once a holdout is exposed, I treat it as seen and do not reuse it as a hidden test.

See [reproducibility.md](docs/reproducibility.md) for the full protocol.

## Run it

```bash
git clone https://github.com/suhaslord/uav-safety-research.git
cd uav-safety-research
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# macOS / Linux: source .venv/bin/activate
pip install -e ".[dev]"
pytest
python scripts/serve_dashboard.py
```

## Next question

Phase 11 will test whether the system can recognize when its uncertainty calibration stops transferring under distribution shift, instead of simply retuning Phase 10R after seeing the failed holdout.

---

**Scope:** educational research · simulation only · `safety_acceptance = false`
