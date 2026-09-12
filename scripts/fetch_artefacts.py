"""Download the pre-trained AURA model artefacts from the GitHub release.

Trained artefacts are not tracked in git (`models/` and `*.pkl` are gitignored), so a fresh
clone has no detector. This pulls the published release asset, verifies its SHA-256, and
extracts it into the layout `aura_api`'s registry expects:

    <dest>/model_metadata.json
    <dest>/pipeline_components/{subject_vectorizer,body_vectorizer,calibrator}.pkl
    <dest>/v1_0/production/phishing_detector_mlp_classifier.pkl

Then point the API at it:

    AURA_MODELS_DIR=/abs/path/to/<dest>

Standard library only — no install step before you can get a model.

Usage:
    python scripts/fetch_artefacts.py                 # -> ./models
    python scripts/fetch_artefacts.py --dest ../aura_api/models
    python scripts/fetch_artefacts.py --force         # re-download over an existing set
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

RELEASE_TAG = "v1"
ASSET = "aura-model-v1.zip"
URL = f"https://github.com/kudzaiprichard/aura-model/releases/download/{RELEASE_TAG}/{ASSET}"
SHA256 = "595a06ef3095f483e9577d0786aae778d87175fed5c37abbc8fc115bd749790c"

# Presence of these means a usable artefact set is already in place.
SENTINELS = (
    Path("model_metadata.json"),
    Path("pipeline_components/subject_vectorizer.pkl"),
    Path("pipeline_components/body_vectorizer.pkl"),
    Path("pipeline_components/calibrator.pkl"),
    Path("v1_0/production/phishing_detector_mlp_classifier.pkl"),
)


def _human(n: int) -> str:
    return f"{n / 1048576:.1f} MB"


def _download(url: str, target: Path) -> None:
    """Stream to disk, printing progress; keeps memory flat for a ~50 MB asset."""
    # Carriage-return progress only makes sense on a terminal; piped to a file or
    # a CI log it would emit hundreds of lines.
    interactive = sys.stdout.isatty()
    with urllib.request.urlopen(url) as response:  # noqa: S310 - fixed https URL
        total = int(response.headers.get("Content-Length") or 0)
        done = 0
        with target.open("wb") as fh:
            while chunk := response.read(1 << 16):
                fh.write(chunk)
                done += len(chunk)
                if interactive:
                    pct = f"{done * 100 // total:3d}%  " if total else ""
                    print(f"\r  {pct}{_human(done)}", end="", flush=True)
    if interactive:
        print()
    else:
        print(f"  downloaded {_human(done)}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_extract(archive: Path, dest: Path) -> None:
    """Extract, refusing any entry that would escape `dest`."""
    with zipfile.ZipFile(archive) as zf:
        for name in zf.namelist():
            resolved = (dest / name).resolve()
            if not str(resolved).startswith(str(dest.resolve())):
                raise RuntimeError(f"refusing unsafe archive entry: {name}")
        zf.extractall(dest)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--dest",
        default=str(Path(__file__).resolve().parent.parent / "models"),
        help="directory to extract into (default: AURA_Model/models)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="re-download even if artefacts are already present",
    )
    args = parser.parse_args()

    dest = Path(args.dest).resolve()

    if not args.force and all((dest / s).exists() for s in SENTINELS):
        print(f"Artefacts already present in {dest}")
        print("Nothing to do. Re-run with --force to replace them.")
        return 0

    dest.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {ASSET} ({RELEASE_TAG})")
    print(f"  from {URL}")

    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / ASSET
        try:
            _download(URL, archive)
        except urllib.error.HTTPError as exc:
            print(f"\nDownload failed: HTTP {exc.code} {exc.reason}", file=sys.stderr)
            print(f"Check that the release exists: {URL}", file=sys.stderr)
            return 1
        except urllib.error.URLError as exc:
            print(f"\nDownload failed: {exc.reason}", file=sys.stderr)
            return 1

        print("Verifying checksum")
        actual = _sha256(archive)
        if actual != SHA256:
            print("  SHA-256 MISMATCH - refusing to extract", file=sys.stderr)
            print(f"    expected {SHA256}", file=sys.stderr)
            print(f"    got      {actual}", file=sys.stderr)
            return 1
        print(f"  ok  {actual[:16]}...")

        if args.force:
            for sentinel in SENTINELS:
                top = dest / sentinel.parts[0]
                if top.is_dir():
                    shutil.rmtree(top, ignore_errors=True)
                elif top.exists():
                    top.unlink()

        print(f"Extracting into {dest}")
        _safe_extract(archive, dest)

    missing = [str(s) for s in SENTINELS if not (dest / s).exists()]
    if missing:
        print("Extraction incomplete, missing:", file=sys.stderr)
        for m in missing:
            print(f"  {m}", file=sys.stderr)
        return 1

    print("\nDone. Point the API at these artefacts:")
    print(f"  AURA_MODELS_DIR={dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
