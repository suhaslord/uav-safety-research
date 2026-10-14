"""Local still-image prototype uses authenticated weights and no ground truth."""
import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest
from scripts import run_prototype_on_images as local


class FakeTensor:
    def __init__(self, values):
        self.values = values
    def cpu(self):
        return self
    def tolist(self):
        return self.values


def output(scores=(.91,.4), classes=(0,0)):
    return SimpleNamespace(boxes=SimpleNamespace(
        xyxyn=FakeTensor([[.1,.1,.3,.3],[.5,.5,.9,.9]][:len(scores)]),
        conf=FakeTensor(list(scores)), cls=FakeTensor(list(classes))))


def setup(tmp_path, monkeypatch):
    photo=tmp_path/"photo.jpg"
    photo.write_bytes(b"test local image fixture")
    weights=tmp_path/"best.pt"
    weights.write_bytes(b"placeholder fixture checkpoint")
    monkeypatch.setattr(local,"CHECKPOINT_SHA256",hashlib.sha256(weights.read_bytes()).hexdigest())
    return photo, weights


def test_label_free_inference_is_a_real_prediction_gate(tmp_path,monkeypatch):
    photo, weights=setup(tmp_path,monkeypatch)
    seen=[]
    class Model:
        def __init__(self,name):
            seen.append(name)
        def predict(self,**kwargs):
            seen.append(kwargs)
            return [output()]
    result=local.run(photo,weights,.5,Model)
    assert len(result["cases"]) == 1
    entry=result["cases"][0]
    assert entry["top_score"] == pytest.approx(.91)
    assert entry["accepted"] is True
    assert entry["top_box"] == [.1,.1,.3,.3]
    assert entry["image_sha256"] == hashlib.sha256(photo.read_bytes()).hexdigest()
    assert result["flight_control_available"] is False
    assert result["labels_used"] is False
    assert result["independent_test_validated"] is False
    assert result["threshold_tuned"] is False
    assert seen[1]["imgsz"] == 320 and seen[1]["conf"] == .001
    assert seen[1]["iou"] == .7 and seen[1]["max_det"] == 300
    assert seen[1]["device"] == "cpu"


def test_no_detection_abstains(tmp_path,monkeypatch):
    photo,weights=setup(tmp_path,monkeypatch)
    class Model:
        def __init__(self,_): pass
        def predict(self,**_):
            return [SimpleNamespace(boxes=None)]
    result=local.run(photo,weights,.05,Model)
    row=result["cases"][0]
    assert row["top_score"] == 0 and row["top_box"] is None and not row["accepted"]


def test_wrong_weight_hash_and_invalid_cutoff_fail_closed(tmp_path,monkeypatch):
    photo,weights=setup(tmp_path,monkeypatch)
    weights.write_bytes(b"tampered")
    with pytest.raises(ValueError,match="authenticated"):
        local.run(photo,weights,.5,lambda _:None)
    with pytest.raises(ValueError,match="Illustrative"):
        local.run(photo,weights,0,lambda _:None)


def test_invalid_detector_box_and_class_fail_closed():
    with pytest.raises(ValueError,match="invalid normalized"):
        local.predictions_from_result(SimpleNamespace(boxes=SimpleNamespace(
            xyxyn=FakeTensor([[.6,.5,.2,.9]]),conf=FakeTensor([.9]),cls=FakeTensor([0]))))
    with pytest.raises(ValueError,match="Invalid prediction class"):
        local.predictions_from_result(SimpleNamespace(boxes=SimpleNamespace(
            xyxyn=FakeTensor([[.1,.1,.2,.2]]),conf=FakeTensor([.9]),cls=FakeTensor([.5]))))


def test_empty_image_folder_and_too_many_frames_rejected(tmp_path):
    with pytest.raises(ValueError,match="1–500"):
        local.image_list(tmp_path)
    for i in range(501):
        (tmp_path/f"{i}.jpg").write_bytes(b"x")
    with pytest.raises(ValueError,match="1–500"):
        local.image_list(tmp_path)
