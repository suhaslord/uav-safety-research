# Real landing-pad transfer baseline

**Dataset:** KIOS Aerial Landing Pad, Unreal Engine Dataset — **422 real-video images**  
**Evaluation:** unchanged `ThresholdPadEstimator`; no retraining or tuning  
**Workflow:** GitHub Actions run `34930371598`

| Metric | Result |
| --- | ---: |
| Images evaluated | **422** |
| Valid estimate rate | **76.8%** |
| Horizontal-center MAE | **0.2176 image widths** |
| Horizontal-center P95 error | **0.5146 image widths** |
| Predicted x inside annotated landing-pad box | **30.6%** |
| Mean confidence | **0.520** |

## Interpretation

The simple synthetic threshold-centroid heuristic **does not transfer well to the real-video subset**. It failed to return a valid estimate on about 23% of frames, and among valid estimates the predicted horizontal position landed inside the annotated pad box only about 31% of the time.

That is useful negative evidence: the 96×96 synthetic benchmark was too easy to stand in for real camera imagery. The next perception stage should use a real-image detector/segmenter with a protected evaluation split rather than tuning this old heuristic on the same 422 frames.

This is **not an object-detection mAP result** because the frozen baseline outputs a horizontal position, not a full bounding box.
