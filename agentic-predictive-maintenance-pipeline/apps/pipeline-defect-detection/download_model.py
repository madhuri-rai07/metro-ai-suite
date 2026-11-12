#!/usr/bin/env python3
# SPDX-FileCopyrightText: (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

"""Download the reviewed detector and notices without overwriting local models."""

import hashlib
import os
from pathlib import Path
import tempfile
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, build_opener


REPOSITORY = "open-edge-platform/apm-pipeline-defect-detection"
REVISION = "86a3169310e91fcdaea0aab45f1ade616fced081"
# Pin sizes as well as hashes to reject truncated or unexpectedly large responses.
ARTIFACTS = {
    "model.xml": (748634, "e98d650e30ee5a388ba313b109fe84f685c5eb12d5d661f2e219b0ad6dc2fdc4"),
    "model.bin": (108233378, "3bc86ec5fc052a0515914628382a15e8ab63486da23b115fba226b52481a4dd5"),
    "model.json": (284, "86f841ced04cd50af96928b717c42430ae3583c541fefc0635170bf07845a013"),
    "model.json.license": (87, "9e2d691dfd26a341bf441e69d894b4fc8d2538318c72f636539a0d73c67d0f51"),
    "LICENSE": (11358, "cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30"),
    "DATASET_ATTRIBUTION.txt": (
        4312, "9970973bd3ec19e5997708d49623d6bd25f3ed90384912f523221a12a44eb54e"
    ),
    "README.md": (12173, "3eaeb7f91df45358fe3b0821ba18b56a8c00027f64eed3571a68a79082a7aca4"),
}


class HTTPSRedirectHandler(HTTPRedirectHandler):
    """Allow HF's CDN redirects without downgrading transport security."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlsplit(newurl).scheme != "https":
            raise ValueError("Model downloads require HTTPS redirects")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


OPENER = build_opener(HTTPSRedirectHandler())


def verify_artifact(path, expected_size, expected_hash):
    """Reject missing, redirected, truncated, or modified cached artifacts."""
    if path.is_symlink() or not path.is_file() or path.stat().st_size != expected_size:
        raise ValueError(f"Missing or invalid model artifact: {path.name}")
    with path.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    if actual != expected_hash:
        raise ValueError(f"SHA-256 mismatch: {path.name}")


def download_model(models_dir):
    """Install a complete, verified revision atomically; reuse only a valid cache."""
    cache = Path(models_dir) / "hf"
    if cache.is_symlink():
        raise ValueError("The model cache must not be a symlink")
    cache.mkdir(parents=True, exist_ok=True)
    destination = cache / REVISION
    if destination.is_symlink():
        raise ValueError("The model revision directory must not be a symlink")
    if destination.exists():
        for name, (size, checksum) in ARTIFACTS.items():
            verify_artifact(destination / name, size, checksum)
        return destination

    with tempfile.TemporaryDirectory(prefix=".download-", dir=cache) as temporary:
        staged = Path(temporary) / REVISION
        staged.mkdir(mode=0o755)
        for name, (size, checksum) in ARTIFACTS.items():
            url = f"https://huggingface.co/{REPOSITORY}/resolve/{REVISION}/{name}"
            path = staged / name
            with OPENER.open(url, timeout=60) as response, path.open("xb") as output:
                total = 0
                while chunk := response.read(1024 * 1024):
                    total += len(chunk)
                    if total > size:
                        raise ValueError(f"Response exceeds expected size: {name}")
                    output.write(chunk)
            verify_artifact(path, size, checksum)
            path.chmod(0o644)
        staged.chmod(0o755)
        os.rename(staged, destination)
    return destination


if __name__ == "__main__":
    try:
        installed = download_model(Path(__file__).resolve().parent / "models")
    except (OSError, ValueError) as error:
        raise SystemExit(f"Detector download failed: {error}") from error
    print(f"Verified detector and notices: {installed}")
