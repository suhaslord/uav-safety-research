# Phase 5 — Post-Freeze Robustness Validation

## Purpose

The frozen V3 result is strong inside one simulation setup. Phase 5 asks whether the result survives controlled changes **without retuning the V3 algorithm**.

The V3 supervisor and fusion configuration remain fixed. Only the evaluation environment changes.

## Research questions

1. Does V3 generalize across multiple unseen seed families?
2. How does performance change as perception degradation becomes weaker or stronger than the frozen `mixed` profile?
3. How dependent is V3 on the quality and update rate of the independent reference estimate?
4. How much reference-update dropout can V3 tolerate?
5. Across what persistent-bias magnitudes does the bias estimator remain useful?
6. Can the state-level perception surrogate begin to be replaced with a controlled pixel-based front end?

## Architectures

The robustness suite compares:

- baseline
- Aegis V2
- frozen Aegis V3

V1 is retained as a historical result but omitted from the robustness sweep because its dominant failure mode — excessive aborting — has already been established and it substantially increases experiment cost.

## Axis 1 — unseen seed families

Frozen `mixed` and `occlusion` profiles are evaluated across five new top-level seed families:

- 515151
- 626262
- 737373
- 848484
- 959595

Each family generates its own paired episode seeds. Architecture comparisons remain paired within each family.

Primary question:

> Does the V3 advantage remain stable across independent random realizations rather than only seed 424242?

## Axis 2 — degradation strength

The `mixed` profile is rescaled to:

- 0.60x
- 0.80x
- 1.00x
- 1.20x
- 1.40x
- 1.60x

Noise, dropout probability, and persistent lateral bias are changed together. Above 1.0x, confidence is also reduced. These are abstract stress levels, not calibrated camera physics.

Primary question:

> Where does V3 begin to lose safety or availability as perception degradation exceeds the frozen condition?

## Axis 3 — weaker reference estimator

The independent reference estimate is weakened through both increased noise and lower update frequency:

| Scenario | Noise multiplier | Update interval |
|---|---:|---:|
| nominal | 1.0x | 5 steps |
| weaker 1 | 1.5x | 7 steps |
| weaker 2 | 2.0x | 10 steps |
| weaker 3 | 3.0x | 15 steps |

Primary question:

> Is V3 robust to an imperfect second estimate, or does the frozen result depend on the nominal reference being unusually informative?

## Axis 4 — reference dropout

Reference-update dropout probability is swept through:

- 0.00
- 0.12 (nominal)
- 0.25
- 0.40
- 0.60
- 0.75

Primary question:

> How much independent evidence can disappear before V3 loses its advantage?

## Axis 5 — persistent-bias magnitude

`mixed` noise and dropout are held fixed while lateral bias is set to:

- 0.00 m
- 0.20 m
- 0.40 m
- 0.62 m (frozen mixed value)
- 0.80 m
- 1.00 m
- 1.20 m

Primary question:

> Does the bias estimator work only near the value seen in development, or across a broad bias range?

## Reproducibility rules

- No V3 tuning based on Phase 5 results.
- Every stress scenario is stored explicitly in `run_metadata.json`.
- Named historical profiles in `PROFILES` are not modified.
- Baseline, V2, and V3 receive paired episode seeds.
- V3's independent reference estimator retains its isolated RNG stream.
- Raw episode-level outputs are preserved.
- Wilson intervals and paired rescue/regression counts are reported.

If Phase 5 reveals a weakness, that becomes a documented limitation or a future architecture version. It does not justify silently changing frozen V3.

## Commands

### Development-size robustness pass

```bash
python scripts/run_robustness_suite.py --axis seed_families --episodes 50
python scripts/run_robustness_suite.py --axis degradation_strength --episodes 100
python scripts/run_robustness_suite.py --axis reference_quality --episodes 100
python scripts/run_robustness_suite.py --axis reference_dropout --episodes 100
python scripts/run_robustness_suite.py --axis bias_magnitude --episodes 100
```

### Run every axis

```bash
python scripts/run_robustness_suite.py --axis all --episodes 100
```

Results are written under:

```text
results/robustness/<axis>/
```

Each axis writes:

- `episodes.csv`
- `summary.csv`
- `paired_effects.csv`
- `summary.md`
- `run_metadata.json`
- success / unsafe / abort plots

The seed-family axis also writes `family_aggregate.csv`.

## Interpretation

Phase 5 is not a contest to preserve a 97.6% success number under every possible condition. A useful outcome is a **failure boundary**: a clear map of where V3 remains strong, where performance degrades gradually, and where the architecture no longer has enough independent information to correct perception errors.
