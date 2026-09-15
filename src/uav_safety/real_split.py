from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable

from .real_landing_dataset import RealLandingSample


_FRAME_RE = re.compile(r"^(?P<sequence>.+)__(?P<frame>\d+)$")


@dataclass(frozen=True)
class SplitAssignment:
    sample: RealLandingSample
    sequence: str
    frame_index: int
    split: str


def parse_sequence_frame(path: Path) -> tuple[str, int]:
    match = _FRAME_RE.match(path.stem)
    if not match:
        raise ValueError(f"Expected <sequence>__<frame> filename, got {path.name!r}")
    return match.group("sequence"), int(match.group("frame"))


def temporal_split(
    samples: Iterable[RealLandingSample],
    *,
    train_fraction: float = 0.60,
    val_fraction: float = 0.15,
    embargo_fraction: float = 0.05,
) -> list[SplitAssignment]:
    """Split each video sequence in time order with an embargo before test.

    The final fraction is the protected test segment. The embargo segment is
    deliberately unused so adjacent video frames do not sit directly on both
    sides of the validation/test boundary.
    """

    if min(train_fraction, val_fraction, embargo_fraction) < 0:
        raise ValueError("split fractions must be non-negative")
    if train_fraction + val_fraction + embargo_fraction >= 1:
        raise ValueError("fractions must leave a positive test segment")

    by_sequence: dict[str, list[tuple[int, RealLandingSample]]] = {}
    for sample in samples:
        sequence, frame = parse_sequence_frame(sample.image_path)
        by_sequence.setdefault(sequence, []).append((frame, sample))

    assignments: list[SplitAssignment] = []
    for sequence, rows in sorted(by_sequence.items()):
        rows.sort(key=lambda item: item[0])
        n = len(rows)
        if n < 8:
            raise ValueError(f"Sequence {sequence!r} is too short for protected splitting: {n} frames")

        train_end = max(1, int(n * train_fraction))
        val_end = max(train_end + 1, int(n * (train_fraction + val_fraction)))
        embargo_end = max(val_end, int(n * (train_fraction + val_fraction + embargo_fraction)))
        embargo_end = min(embargo_end, n - 1)

        for position, (frame, sample) in enumerate(rows):
            if position < train_end:
                split = "train"
            elif position < val_end:
                split = "val"
            elif position < embargo_end:
                split = "embargo"
            else:
                split = "test"
            assignments.append(SplitAssignment(sample=sample, sequence=sequence, frame_index=frame, split=split))

    return assignments
