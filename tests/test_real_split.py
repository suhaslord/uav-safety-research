from pathlib import Path

from uav_safety.real_landing_dataset import RealLandingSample, YoloBox
from uav_safety.real_split import parse_sequence_frame, temporal_split


def _sample(sequence: str, frame: int) -> RealLandingSample:
    return RealLandingSample(
        image_path=Path(f"{sequence}__{frame}.jpg"),
        label_path=Path(f"{sequence}__{frame}.txt"),
        boxes=(YoloBox(0, 0.5, 0.5, 0.2, 0.2),),
    )


def test_parse_sequence_frame() -> None:
    assert parse_sequence_frame(Path("land_pad2__125.jpg")) == ("land_pad2", 125)


def test_temporal_split_has_protected_test_and_embargo() -> None:
    samples = [_sample("video_a", i * 25) for i in range(20)] + [_sample("video_b", i * 25) for i in range(20)]
    assignments = temporal_split(samples)

    for sequence in ("video_a", "video_b"):
        rows = [row for row in assignments if row.sequence == sequence]
        assert [row.split for row in rows].count("train") == 12
        assert [row.split for row in rows].count("val") == 3
        assert [row.split for row in rows].count("embargo") == 1
        assert [row.split for row in rows].count("test") == 4

        train_frames = [row.frame_index for row in rows if row.split == "train"]
        val_frames = [row.frame_index for row in rows if row.split == "val"]
        embargo_frames = [row.frame_index for row in rows if row.split == "embargo"]
        test_frames = [row.frame_index for row in rows if row.split == "test"]
        assert max(train_frames) < min(val_frames) < min(embargo_frames) < min(test_frames)
