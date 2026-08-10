# Reproducibility Protocol

AegisLand separates **development**, **historical results**, and **frozen evaluation** so improvements are not produced by repeatedly rerunning the same test seed until the numbers look better.

## Historical experiments

- V1 main experiment: seed `2026`, 500 episodes per profile/controller cell
- V2 paired comparison: seed `2027`, 500 episodes per profile/architecture cell

Those results are historical records and should not be replaced after architecture changes.

## V3 development

Use seed `3031` for the first small development run:

```bash
python scripts/run_v3_comparison.py --episodes 30 --seed 3031 --out results/v3_development
```

The purpose of this run is to detect obvious implementation problems and determine whether the architecture is directionally useful. It is not the final reported V3 result.

## V3 frozen evaluation

After the V3 implementation is accepted, run a new seed that was not used during V1/V2/V3 development:

```bash
python scripts/run_v3_comparison.py --episodes 500 --seed 424242 --out results/v3_frozen
```

This produces 10,000 simulated episodes:

- 5 perception profiles
- 4 architectures
- 500 paired episode seeds per profile

## Paired seeds

Within each profile, the same episode seed is supplied to baseline, V1, V2, and V3. V3's additional reference estimator uses its own isolated RNG stream, derived from the episode seed, so it does not consume random draws from the legacy vision/disturbance stream.

## Required files to preserve

For a frozen run, keep:

- `episodes.csv`
- `summary.csv`
- `paired_effects.csv`
- `summary.md`
- `run_metadata.json`
- generated plots

The metadata file stores the V3 supervisor and reference-estimator configuration used for the run.

## Before claiming an improvement

Check all of the following:

1. tests pass;
2. no timeouts dominate a condition;
3. unsafe-touchdown reduction is not explained only by a large abort increase;
4. clean and blur do not regress materially;
5. paired-effect counts support the aggregate-rate conclusion;
6. the frozen seed was not used to tune V3;
7. negative results are retained in the repository.

## Scope

All results in this repository are from a simplified simulation and should be described as **simulated landing outcomes**, not real-aircraft safety performance.
