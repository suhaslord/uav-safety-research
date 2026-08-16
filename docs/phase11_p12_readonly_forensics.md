# Phase 11 P12 read-only post-transfer forensics

## Status

**DESCRIPTIVE ONLY — P12 IS FROZEN — NO P12 RETUNING AUTHORIZED**

These diagnostics use only already-exposed P12 calibration and seen-transfer artifacts. They may motivate a future preregistered revision but may not alter P12 or make seed `605605` unseen again.

Protected validation seed `616616` remains unexposed and retired with P12.

## Natural-stream check

The P12 event-stratified transfer failure is not explained by the forced-outage intervention alone.

On the same fresh transfer trajectories with **no forced dropout intervention**, the frozen P12 candidate still undercovered:

- natural lateral 95% coverage: `85.95%`;
- natural altitude 95% coverage: `85.59%`;
- natural calibration-curve MACE: `0.18065`;
- natural continuity lateral 95% coverage: `84.54%`;
- natural continuity altitude 95% coverage: `79.97%`;
- natural base lateral 95% coverage: `86.13%`;
- natural base altitude 95% coverage: `86.31%`.

Thus the event-stratified and natural-stream transfer results point in the same direction: the fixed P12 group radii are too small for the fresh compositional transfer regime.

## Within-group severity shift

The inference-visible inherited severity score shifted upward from P12 calibration to P12 transfer **inside every fixed conformal group**.

| Group | Calibration mean severity | Transfer mean severity | Calibration median | Transfer median |
|---|---:|---:|---:|---:|
| `base_output` | `0.3723` | `0.5463` | `0.3059` | `0.4950` |
| `continuity_h3` | `0.3232` | `0.4827` | `0.3190` | `0.4863` |
| `continuity_h45` | `0.2601` | `0.4387` | `0.2686` | `0.4594` |
| `continuity_h67` | `0.2506` | `0.3947` | `0.2694` | `0.3948` |

So source/horizon membership does not make calibration and transfer exchangeable with respect to the already-available severity signal.

## Residual-tail shift within the same groups

P95 absolute errors also increased substantially inside every group:

| Group | Lateral p95 calibration | Lateral p95 transfer | Altitude p95 calibration | Altitude p95 transfer |
|---|---:|---:|---:|---:|
| `base_output` | `0.1711 m` | `0.3300 m` | `0.4143 m` | `0.7952 m` |
| `continuity_h3` | `0.3620 m` | `0.6467 m` | `0.5450 m` | `0.9728 m` |
| `continuity_h45` | `0.4699 m` | `0.7427 m` | `0.6333 m` | `1.0278 m` |
| `continuity_h67` | `0.6247 m` | `0.9574 m` | `0.6788 m` | `1.1148 m` |

The transfer residual shift is therefore not limited to long continuity horizons. Base outputs approximately doubled their p95 residual scale as the compositional severity distribution changed.

## Descriptive calibration-severity stratification

Using calibration-derived within-group severity tertiles **only as a post-exposure descriptive diagnostic**, transfer coverage is concentrated in the low/middle severity regions and collapses in the high-severity region.

Examples:

- `base_output`, transfer high-severity bin: about `80.2%` lateral / `81.0%` altitude coverage;
- `continuity_h3`, transfer high-severity bin: about `85.4%` lateral / `79.1%` altitude;
- `continuity_h45`, transfer high-severity bin: about `86.7%` lateral / `78.1%` altitude;
- `continuity_h67`, transfer high-severity bin: about `88.2%` lateral / `74.6%` altitude.

These tertiles are **not** proposed P13 thresholds and may not be copied into a new method as if they were preregistered. They only demonstrate that an inference-visible severity axis is associated with the frozen P12 undercoverage.

## Interpretation

P12 isolated the missing variable more clearly than prior revisions:

1. controlled rare-gap study design solved the calibration-power problem;
2. direct group-only conformal intervals remained efficient but undercovered on fresh transfer;
3. undercoverage also appeared on the natural stream, so it is not caused solely by event balancing;
4. severity changed sharply within every horizon/source group;
5. residual tails grew with the same transfer shift;
6. trajectory-level severity already discriminated the regimes with AUROC `0.9989`.

The next revision should therefore test **severity-conditioned direct conformal calibration**, while retaining P12's event-stratified rare-gap design and avoiding the stacked learned uncertainty architecture that made P8 excessively conservative.

A scientifically cleaner design than choosing severity cutpoints from P12 is to use a fresh P13 partition/fitting split to freeze the severity partition, then use a separate fresh calibration split to compute conformal radii. Transfer and protected validation must remain disjoint and unseen until their staged checkpoints.

## Claim boundaries

- descriptive post-exposure analysis only;
- `simulation_only = true`;
- `safety_acceptance = false`;
- `controller_tuning_allowed = false`;
- no physical-flight validation claim;
- no controller-performance claim;
- no new raw-camera accuracy claim.
