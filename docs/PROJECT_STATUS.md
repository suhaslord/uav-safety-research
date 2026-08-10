# Project Status

## AegisLand — Phase 1

**Research question:** Can an uncertainty-aware supervisory layer reduce unsafe simulated UAV landings under degraded perception without creating an impractically high intervention/abort burden?

### Infrastructure

- [x] Planar landing simulator
- [x] Baseline controller
- [x] Perception stress model
- [x] Interpretable safety supervisor
- [x] Monte Carlo runner
- [x] Raw CSV outputs
- [x] Confidence intervals
- [x] Threshold sweep
- [x] Automated tests
- [x] GitHub Actions CI configuration

### Research process

- [x] Research plan
- [x] Methodology document
- [x] Literature starting map
- [x] Ethics / safety scope
- [x] Phase 1 preregistration
- [x] Research log
- [x] External reviewer guide
- [x] Results publication checklist
- [x] Paper workspace

### Next gate

- [ ] Verify CI passes
- [ ] Decide whether to pair identical episode seeds across baseline/supervised conditions
- [ ] Run preregistered 5,000-episode Phase 1 experiment
- [ ] Publish results exactly as specified in the frozen protocol

### Rule

Do not move to a more complicated perception model until the current experiment has taught us something useful.