# Phase 22 controlled occlusion investigation

**Original gate: FAILED. Treatment inference: NOT RUN. Hypothesis: INCONCLUSIVE.**

This publication restores the verified results recorded in the conversation.
The workspace subsequently rolled back and lost the original generated files,
full runtime inventory, input locks, and local commits. Read
`restoration_record.json` for the exact boundary of recoverable evidence.
No detector evaluation was rerun while publishing this recovery.

## Recorded findings

- The exact persistent Phase 22 recovery bundle and checkpoint hashes passed.
- All 86 source frames and 516 frame-dose cases were reconstructed and verified.
- The complete 516-case image CSV reproduced its original checksum exactly.
- All images decoded fully, matched the expected pixels, and passed mask checks.
- The original raw JPEG control failed the 0.001 aggregate tolerance.
- A separate benchmark-clean diagnostic reproduced all four historical clean
  metrics exactly under the same checkpoint and evaluation runtime.
- The original evaluation stopped before any nonzero-dose predictions.
- The earlier focused execution recorded 46 tests passing in 6.65 seconds.

| Metric | Published clean reference | Raw zero-dose result | Benchmark-clean diagnostic |
| --- | ---: | ---: | ---: |
| Precision | 0.7959713659654185 | 0.773365821502563 | 0.7959713659654185 |
| Recall | 0.38372093023255816 | 0.38372093023255816 | 0.38372093023255816 |
| mAP50 | 0.42662686781189296 | 0.42390766686341674 | 0.42662686781189296 |
| mAP50–95 | 0.2723431563204893 | 0.27146222235688644 | 0.2723431563204893 |

The original gate compares recall and mAP50 against the committed Phase 23
comparison CSV, which differs from the released table at floating-point
serialization precision. Its raw-control mAP50 delta is
**-0.0027192009484761637**, outside the unchanged **0.001** tolerance.

## Why the control failed

The sweep protocol preserves raw source JPEG bytes at zero dose. The published
stress benchmark converts even its clean images to RGB and re-encodes them as
JPEG quality 95. The two inputs have different bytes. The clean-only diagnostic
rebuilt and hash-verified the exact published clean inventory; it reproduced all
four released clean metrics with zero numerical difference.

This identifies an input-definition mismatch in reproduction. It does not
establish the mechanism of occlusion failure. The diagnostic never replaced
the original gate or authorized treatment inference.

## Preserved identities

| Record | SHA-256 |
| --- | --- |
| Unchanged original protocol | `e169e16ea40ca44ee60ca8b6074d054c33aeeaf1a3d24e55fa4cd3b8581882d7` |
| Released bundle | `8d6eda7f8775ad899be7a8b6fbf9e6dea30678c1e28c0b687a88184ac592288b` |
| Phase 22 checkpoint | `3a1801b192d624f8dcdda4bc5d9a9157309000df67a4c30d62368c37901feddd` |
| Earlier complete image manifest | `eb2c4202dcd36f792f0a767986bdc3369e32b04d36360ee9fc7ac6db5f7ead28` |
| Earlier target-mask manifest | `76f00fe7050e629a319b9b4d1fb65a0d45c6e9bd127f8f075b2d264d5a4d9554` |
| Published clean inventory | `2412380094b505c1c21e4dfba9333e534d00ac77ac48fcf12b6b72d709c85316` |

The original protocol is restored byte for byte. Its Phase 23 availability
sentence describes its original freeze-time context; the separate later
Phase 23 study was not changed or evaluated here.

The restored runner preserves the recorded doses, mask geometry, raw JPEG
control, exact release hashes, inference settings, full-manifest checksum,
runtime rejection, and stop-before-treatment gate. It uses separate new
implementation/input lock paths because the original full receipts were lost.
Its source is not asserted to be byte-identical to the lost implementation.

## Limits

There are no measured recall, IoU, or confidence outcomes at nonzero doses.
There is no dose-response figure or evidence of a threshold. The frames were
already used for evaluation and come from only two source sequences. The
protocol permits descriptive exploration, not independence claims or
population significance tests. Annotation-box visibility is a proxy, not actual
visible landing-pad surface area. No flight-safety claim follows.

The original full input/runtime receipts remain missing. Historical hashes
and restored metric records do not replace those files. A fresh implementation
recovery and input verification would be needed before any new evaluation.

The original frozen experiment remains failed at its gate. A scientifically
correct follow-up requires a separate versioned protocol whose clean reference
matches its input definition; the original reference was not changed here.
