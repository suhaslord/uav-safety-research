from __future__ import annotations

from pathlib import Path
import argparse
import hashlib
import shutil
import subprocess
import urllib.request


ZENODO_RECORD = "https://zenodo.org/records/13682584"
ARCHIVE_URL = "https://zenodo.org/records/13682584/files/airisim_dataset2.7z?download=1"
ARCHIVE_MD5 = "865515c2d8f5e9cd9b2ee1e1ec294270"
ARCHIVE_NAME = "airisim_dataset2.7z"


def md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(ARCHIVE_URL, headers={"User-Agent": "AegisLand/real-dataset-benchmark"})
    with urllib.request.urlopen(request) as response, path.open("wb") as output:
        total = int(response.headers.get("Content-Length", "0"))
        copied = 0
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            output.write(chunk)
            copied += len(chunk)
            if total:
                print(f"downloaded {copied / 1e6:.0f}/{total / 1e6:.0f} MB", end="\r")
    print()


def extract(archive: Path, destination: Path) -> None:
    seven_zip = shutil.which("7z") or shutil.which("7zz")
    if not seven_zip:
        raise SystemExit("7z/7zz was not found. Install 7-Zip (Windows) or p7zip-full (Linux), then rerun with --extract.")
    destination.mkdir(parents=True, exist_ok=True)
    subprocess.run([seven_zip, "x", "-y", str(archive), f"-o{destination}"], check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download the public KIOS Aerial Landing Pad / Unreal Engine dataset.")
    parser.add_argument("--out", type=Path, default=Path("data/external/kios_landing_pad"))
    parser.add_argument("--extract", action="store_true")
    parser.add_argument(
        "--accept-download",
        action="store_true",
        help="Required acknowledgement before downloading the ~639 MB public archive.",
    )
    args = parser.parse_args()

    if not args.accept_download:
        raise SystemExit(
            "This downloads ~639 MB from Zenodo. Review the dataset source/citation first: "
            f"{ZENODO_RECORD}\nThen rerun with --accept-download."
        )

    archive = args.out / ARCHIVE_NAME
    if not archive.exists():
        download(archive)
    else:
        print(f"Using existing archive: {archive}")

    checksum = md5(archive)
    if checksum != ARCHIVE_MD5:
        raise SystemExit(f"MD5 mismatch: expected {ARCHIVE_MD5}, got {checksum}")
    print(f"MD5 verified: {checksum}")

    if args.extract:
        extract(archive, args.out / "extracted")
        print(f"Extracted to {args.out / 'extracted'}")
    else:
        print("Archive verified. Add --extract to unpack it.")


if __name__ == "__main__":
    main()
