"""Keep scientific runtimes stable and adapt synthetic fixtures, not frozen methods."""
import os
from pathlib import Path

import pytest

# A malformed-image unit test must never trigger an inference-library package
# upgrade. This is set before test module collection/imports.
os.environ["YOLO_AUTOINSTALL"] = "False"


@pytest.fixture(autouse=True)
def recovered_fixture_native_paths(request, monkeypatch):
    """Retain exact f090da03 tests/runner; normalize generated fixture paths only."""
    if os.name != "nt" or request.module.__name__ != "test_phase25_occlusion_sweep_publication":
        return
    build = request.module.fixture_inputs

    def native_fixture(*args, **kwargs):
        root, cases, masks, seal = build(*args, **kwargs)
        for case in cases:
            for field in ("image_path", "label_path"):
                case[field] = str(Path(case[field]))
        seal()
        return root, cases, masks, seal

    monkeypatch.setattr(request.module, "fixture_inputs", native_fixture)
