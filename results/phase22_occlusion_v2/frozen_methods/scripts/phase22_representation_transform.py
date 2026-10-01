"""Byte-defined Phase 22 follow-up representations; no detector dependencies."""
from __future__ import annotations

import hashlib
import io
import os
from pathlib import Path
import tempfile

import numpy as np
from PIL import Image, JpegImagePlugin

REPRESENTATIONS = ("RAW_SOURCE", "HISTORICAL_Q95", "Q90", "Q100", "LOSSLESS_PNG")
QUALITIES = {"HISTORICAL_Q95": 95, "Q90": 90, "Q100": 100}


def encode(source: bytes, representation: str) -> bytes:
    if representation not in REPRESENTATIONS:
        raise ValueError("Unknown representation")
    if representation == "RAW_SOURCE":
        return source
    with Image.open(io.BytesIO(source)) as image:
        rgb = image.convert("RGB")
        output = io.BytesIO()
        if representation == "LOSSLESS_PNG":
            rgb.save(output, format="PNG", optimize=False, compress_level=6)
        else:
            # Identical to the historical clean path: convert RGB, save quality=95.
            # Defaults (including subsampling) are deliberately not overridden.
            rgb.save(output, format="JPEG", quality=QUALITIES[representation])
        return output.getvalue()


def atomic_write(path: Path, content: bytes, expected_sha256: str, *, image: bool = False) -> None:
    """Reject corrupt bytes before publishing; never replace different frozen content."""
    if hashlib.sha256(content).hexdigest() != expected_sha256:
        raise ValueError("Atomic writer content SHA mismatch")
    if image:
        with Image.open(io.BytesIO(content)) as opened:
            opened.verify()
        with Image.open(io.BytesIO(content)) as opened:
            opened.load()
    if path.exists():
        if path.read_bytes() != content:
            raise ValueError(f"Refusing to overwrite frozen content: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if hashlib.sha256(temporary.read_bytes()).hexdigest() != expected_sha256:
            raise ValueError("Atomic writer disk SHA mismatch")
        if image:
            with Image.open(temporary) as opened:
                opened.load()
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)


def image_difference(source: bytes, derived: bytes) -> dict:
    with Image.open(io.BytesIO(source)) as opened:
        a = np.asarray(opened.convert("RGB"), dtype=np.float64)
    with Image.open(io.BytesIO(derived)) as opened:
        b = np.asarray(opened.convert("RGB"), dtype=np.float64)
        size = opened.size
        codec = opened.format
        sampling = JpegImagePlugin.get_sampling(opened) if codec == "JPEG" else None
    if a.shape != b.shape:
        raise ValueError("Representation changed dimensions")
    difference = a - b
    rmse = float(np.sqrt(np.mean(difference ** 2)))
    return {"width": size[0], "height": size[1], "codec": codec,
            "subsampling": sampling, "file_size": len(derived),
            "file_size_delta": len(derived) - len(source),
            "pixel_mae": float(np.mean(np.abs(difference))), "pixel_rmse": rmse,
            "psnr_db": float(20 * np.log10(255 / rmse)) if rmse else None,
            "pixels_identical": rmse == 0}
