# AegisLand project understanding guide

This document is the **start-here explanation of the project at a block level**. The goal is to be able to explain each part clearly before adding more complexity.

![AegisLand research cockpit](assets/readme/frame_home.png)

## 1. The project in plain English

AegisLand studies a simple safety question:

> If a drone's landing perception becomes unreliable, can the system notice that before it trusts a bad estimate too much?

The project is simulation-only. It does not fly a real drone and does not prove real-world flight safety.

A simple way to explain it to a non-technical person:

> A drone needs to estimate where it is relative to a landing area. I simulate cases where that estimate gets worse because of things such as blur-like degradation, low light, occlusion, noise, bias, or stale observations. Then I compare a normal landing system with a safety-supervised version that can slow down, hold, or abort when the estimate looks untrustworthy.

## 2. High-level pipeline

```mermaid
flowchart LR
    A[Simulated drone state] --> B[Perception / image block]
    B --> C[Estimated position + confidence]
    C --> D[Safety supervisor]
    D --> E[Landing controller]
    E --> F[Simulated drone motion]
    F --> G[Outcome metrics]
```

For the pixel-based image benchmark, the perception block can be expanded as:

```mermaid
flowchart LR
    A[True lateral offset + altitude] --> B[Synthetic 96x96 landing-pad image]
    B --> C[Degradation block]
    C --> D[Threshold-based pad estimator]
    D --> E[Estimated lateral position + confidence + valid/invalid]
```

## 3. What goes into and comes out of each block

| Block | Input | What it does | Output | Main code |
|---|---|---|---|---|
| Drone simulation | position, altitude, velocity | updates simulated motion | new state | `src/uav_safety/dynamics.py`, simulator files |
| Abstract perception | true state + selected stress profile | adds controlled noise, bias, dropout/staleness and imperfect confidence | perceived state + confidence | `src/uav_safety/perception.py` |
| Synthetic image renderer | lateral offset, altitude, condition, severity | creates a simple 96x96 grayscale landing-pad image and applies a visual degradation | grayscale image | `src/uav_safety/image_perception.py` |
| Pad estimator | grayscale image | thresholds bright pixels and computes a weighted centroid | lateral estimate, confidence, validity | `ThresholdPadEstimator` in `image_perception.py` |
| Safety supervisor | perceived state, confidence, uncertainty/risk signals | decides whether to proceed, hold, or abort | safety decision | supervisor modules |
| Controller | perceived state + safety decision | generates the landing command used by the simulator | commanded motion | `src/uav_safety/controller.py` and simulator files |
| Metrics | completed simulated episode | measures success, unsafe touchdown, error, aborts, etc. | summary results | `src/uav_safety/metrics.py`, experiment scripts |

## 4. What "blur" currently means

There are two different uses of degradation names in the repository, and they should not be mixed up.

### Abstract perception profile

In `src/uav_safety/perception.py`, names such as `blur`, `low_light`, `occlusion`, and `mixed` are **shorthand stress profiles**. They change quantities such as position noise, velocity noise, dropout probability, lateral bias, and confidence. They are not physical camera models.

### Pixel-based image benchmark

In `src/uav_safety/image_perception.py`, `blur` is implemented as repeated **3x3 box-blur passes** over the synthetic grayscale frame. The number of passes increases with the severity setting.

This is intentionally simple. It should be described as a controlled blur-like degradation, **not** as a calibrated model of drone vibration, lens defocus, water on a lens, or a specific real camera failure.

For the current learning stage, blur, low light, occlusion, and mixed degradation should be treated as **blocks with adjustable severity**. A detailed physical derivation of each effect is future work, not a requirement for understanding the system now.

## 5. What the image "detector" actually is

The current pixel front end is **not a neural network** and it does not use OpenCV.

The `ThresholdPadEstimator` is an interpretable classical image-processing baseline:

1. measure the image median, standard deviation, and 90th percentile;
2. create a threshold from those statistics;
3. select pixels above the threshold;
4. compute a brightness-weighted horizontal centroid;
5. convert that centroid into an estimated lateral offset;
6. compute a simple confidence score using image contrast and the amount of supporting pixels.

The main libraries used by this benchmark are:

- NumPy
- pandas
- Matplotlib

At this stage, the important skill is being able to **use the tools correctly and explain the input/output behavior**. A full mathematical derivation of every algorithm can come later as the linear algebra, probability, and calculus background becomes stronger.

## 6. What the dataset is

The first pixel benchmark does **not** use an external real-world dataset.

It generates synthetic 96x96 grayscale landing-pad frames from randomized lateral offsets and altitudes. In the Phase 5 benchmark:

- 5 conditions were used: clean, blur, low light, occlusion, mixed;
- 300 images were generated per condition;
- 1,500 images were evaluated total.

That makes this a controlled synthetic benchmark, not a real-camera validation.

To generate the actual condition examples locally:

```bash
python scripts/run_image_perception_benchmark.py --samples 300 --seed 606060 --out results/image_perception
```

The script produces `results/image_perception/example_conditions.png`, along with the raw sample table, summary table, and plots. That generated figure is the preferred image to show when explaining what the five pixel-level conditions look like.

## 7. Current pixel-benchmark result

Phase 5 reported:

| Condition | Valid estimates | Mean absolute lateral error | 95th-percentile error | Mean confidence |
|---|---:|---:|---:|---:|
| Clean | 100% | 0.017 m | 0.031 m | 0.833 |
| Blur | 100% | 0.016 m | 0.030 m | 0.783 |
| Low light | 100% | 0.074 m | 0.255 m | 0.636 |
| Occlusion | 100% | 0.082 m | 0.194 m | 0.818 |
| Mixed | 100% | 0.344 m | 1.002 m | 0.518 |

The most important result is not that blur made the benchmark fail. In this simple synthetic setup, blur barely changed lateral-estimation error. The clearest failure was **mixed degradation**: error increased substantially, but the estimator still returned a valid estimate for every image.

That means a major research issue is not just image quality. It is whether the system knows **when not to trust its own estimate**.

![Later Phase 6B perception result](assets/readme/chart_phase6b_light.png)

The image above is from later perception work. It is useful context, but it should not be presented as if it were the original Phase 5 benchmark.

## 8. What "baseline" means

There are two baselines in different parts of the project.

### Image-estimation baseline

`ThresholdPadEstimator` is the simple classical image-processing baseline for the pixel benchmark.

### Landing-system baseline

In the control experiments, the **baseline architecture** attempts the landing without using the safety supervisor. The supervised architectures add confidence/risk logic that can intervene.

Whenever results are shown, the document should say which baseline is being discussed.

## 9. How to document every block

For each important component, use the same small template:

### Purpose

What job does this block perform in one sentence?

### Input

What exact values or objects enter the block?

### Transformation

What does the block do at a high level? Avoid hiding behind the phrase “the algorithm.”

### Output

What exact values leave the block and which later block consumes them?

### Assumptions

What has been simplified? What should not be interpreted as real-world physics?

### Code pointer

Which file/class/function implements the block?

### Reference

If deeper knowledge is needed, link a paper, textbook section, library documentation page, or other reliable technical resource.

### Example

Give one concrete input/output example that could be explained to a non-technical person.

This template should be used whenever a component is expanded in the future.

## 10. How to communicate an experiment

Every experiment should be understandable in this order:

1. **Problem:** what are we trying to learn?
2. **Data:** what frames, states, or samples are being used?
3. **Method:** what blocks/algorithms process the data?
4. **Experiment:** what is changed and what is held fixed?
5. **Metric:** what numerical outcome answers the question?
6. **Result:** what actually happened?
7. **Limitation:** what does the result not prove?
8. **Next step:** what is the smallest useful follow-up?

This mirrors the structure of a research paper without forcing the project to become a paper yet.

## 11. Current learning/research scope

The immediate goal is **system-level understanding**, not deep mathematical specialization in one degradation model.

For now:

- understand how each block connects to the next;
- become comfortable with NumPy, pandas, Matplotlib, and running/reading the benchmark code;
- know how to run a detector/estimator and interpret its output;
- document assumptions and limitations;
- organize results clearly;
- explain the project without technical jargon.

Later, after stronger linear algebra, probability, calculus, and imaging background, a narrower component could be studied in depth—for example a physically meaningful motion-blur model or a more advanced perception method.

## 12. Paper-style learning without forcing a paper

A useful future habit is to read strong research papers mainly for their **structure**:

- abstract / problem statement;
- related context;
- dataset or experimental evidence;
- method;
- evaluation protocol;
- results;
- limitations;
- conclusion.

The current project should borrow that organization now. A formal paper submission is a later decision, only after the technical understanding and evidence support a focused claim.

## 13. What the project currently claims

Supported:

- controlled simulation can test how perception degradation changes landing estimates and decisions;
- the project can compare an unsupervised landing architecture with confidence-aware safety supervision;
- the synthetic image benchmark exposes cases where the estimator can remain confident/valid despite larger error;
- the repository preserves reproducible experiments, seeds, and frozen evaluation stages.

Not supported:

- real-drone safety;
- real-camera performance;
- a physically accurate model of blur, low light, or occlusion;
- certification or deployment readiness;
- the claim that these results directly transfer to spacecraft landing.

## 14. Work completed from the research feedback

- [x] define the project in plain English;
- [x] write the high-level system pipeline;
- [x] identify the input/output of each main block;
- [x] document what blur and the other named conditions actually mean;
- [x] document the exact pixel estimator instead of calling it a generic detector;
- [x] state what the dataset really is;
- [x] collect the key Phase 5 image results in one place;
- [x] reorganize the root README into problem → data → method → experiment → result → limitation;
- [x] add existing project/result visuals to the root README and this guide;
- [x] add a repeatable documentation template for each block;
- [x] add a research-experiment communication template;
- [ ] keep improving individual block documentation with references as needed;
- [ ] run the image benchmark locally when a fresh `example_conditions.png` is needed for a presentation/update;
- [ ] practice the 60-second explanation without referring to the website;
- [ ] only later choose a narrow paper-style research question if the evidence justifies it.

## 15. 60-second explanation

> AegisLand is a simulation project about safer autonomous drone landing. A landing system has to estimate where the drone is, but those estimates can become unreliable when visual information gets degraded or stale. I simulate those failures and compare a normal landing system with a supervised system that looks at confidence and independent evidence before deciding whether to continue, hold, or abort. I also built a small synthetic image benchmark that generates landing-pad images under conditions like blur, low light, and occlusion. The current image estimator is intentionally simple and rule-based. One important result is that under harder mixed degradation it can still return a valid answer even when its error becomes much larger, which shows why knowing when not to trust perception is an important part of the problem.

## 16. Code pointers

Start here when reviewing the implementation:

1. `src/uav_safety/image_perception.py` — synthetic images, degradation blocks, threshold estimator.
2. `scripts/run_image_perception_benchmark.py` — how the image benchmark is generated and summarized.
3. `src/uav_safety/perception.py` — abstract perception stress profiles.
4. `docs/methodology.md` — high-level simulation and safety-supervisor methodology.
5. `docs/phase5_results.md` — first synthetic image benchmark and measured limitations.
6. `README.md` — public-facing problem/data/method/result/limitation explanation.

The goal is to understand these files well enough to explain what each block receives, what it changes, and what it returns.