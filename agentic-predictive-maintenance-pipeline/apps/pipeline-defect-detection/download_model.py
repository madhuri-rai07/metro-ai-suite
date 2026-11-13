#!/usr/bin/env python3
# SPDX-FileCopyrightText: (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

"""Install the pinned detector through the model-download microservice."""

import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import time


REPOSITORY = "open-edge-platform/apm-pipeline-defect-detection"
REVISION = "86a3169310e91fcdaea0aab45f1ade616fced081"
SERVICE_DOWNLOAD_PATH = f"hf-downloads/{REVISION}"
DOWNLOAD_TIMEOUT = 1800
POLL_INTERVAL = 2
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


def service_request(port, path, body=None):
    """Call only the local service, without proxies or HTTP redirects."""
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
    try:
        connection.request(
            "GET" if body is None else "POST",
            f"/api/v1/{path}",
            body=None if body is None else json.dumps(body),
            headers={"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        if response.status != 200:
            raise RuntimeError(f"model-download returned HTTP {response.status}")
        payload = response.read(1024 * 1024 + 1)
        if len(payload) > 1024 * 1024:
            raise ValueError("model-download response exceeds the size limit")
        result = json.loads(payload)
        if not isinstance(result, dict):
            raise ValueError("Invalid model-download response")
        return result
    finally:
        connection.close()


def download_snapshot(port):
    """Ask the service for the exact HF revision, without OpenVINO conversion."""
    response = service_request(port, f"models/download?download_path={SERVICE_DOWNLOAD_PATH}", {
        "models": [{
            "name": REPOSITORY, "hub": "huggingface", "revision": REVISION,
            "is_ovms": False,
        }],
        "parallel_downloads": False,
    })
    jobs = response.get("job_ids")
    if (not isinstance(jobs, list) or len(jobs) != 1
            or not isinstance(jobs[0], str)
            or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", jobs[0])):
        raise ValueError("Expected one model-download job ID")
    job_id = jobs[0]
    print(f"model-download job: {job_id}", flush=True)
    deadline = time.monotonic() + DOWNLOAD_TIMEOUT
    while time.monotonic() < deadline:
        job = service_request(port, f"jobs/{job_id}")
        if job.get("model_name") != REPOSITORY or job.get("hub") != "huggingface":
            raise ValueError("model-download returned an unexpected model job")
        status = job.get("status")
        if status == "completed":
            return
        if status in {"failed", "canceled"}:
            raise RuntimeError(f"model-download job {job_id} {status}; check the service logs")
        if status not in {"queued", "downloading", "processing"}:
            raise ValueError("Unexpected model-download job status")
        time.sleep(POLL_INTERVAL)
    raise TimeoutError(
        f"model-download job {job_id} timed out; check the service before retrying"
    )


def reject_symlinks(path):
    """Reject redirected model directories, including intermediate parents."""
    if any(parent.is_symlink() for parent in (path, *path.parents)):
        raise ValueError("Model directories must not contain symlinks")


def verify_artifact(path, expected_size, expected_hash):
    """Reject missing, redirected, truncated, or modified cached artifacts."""
    if path.is_symlink() or not path.is_file() or path.stat().st_size != expected_size:
        raise ValueError(f"Missing or invalid model artifact: {path.name}")
    with path.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    if actual != expected_hash:
        raise ValueError(f"SHA-256 mismatch: {path.name}")


def install_snapshot(source, destination):
    """Publish only verified files, leaving the service's download cache intact."""
    reject_symlinks(source)
    reject_symlinks(destination)
    for name, (size, checksum) in ARTIFACTS.items():
        verify_artifact(source / name, size, checksum)
    with tempfile.TemporaryDirectory(prefix=".install-", dir=destination.parent) as temporary:
        staged = Path(temporary) / REVISION
        staged.mkdir(mode=0o755)
        for name, (size, checksum) in ARTIFACTS.items():
            path = staged / name
            shutil.copyfile(source / name, path)
            verify_artifact(path, size, checksum)
            path.chmod(0o644)
        staged.chmod(0o755)
        os.rename(staged, destination)
    return destination


def download_model(models_dir, port=8200):
    """Reuse a valid installation or install a verified service-downloaded snapshot."""
    if not 1 <= port <= 65535:
        raise ValueError("model-download port must be between 1 and 65535")
    models_dir = Path(models_dir)
    destination = models_dir / "hf" / REVISION
    reject_symlinks(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        for name, (size, checksum) in ARTIFACTS.items():
            verify_artifact(destination / name, size, checksum)
        return destination

    source = models_dir / SERVICE_DOWNLOAD_PATH / "huggingface" / REPOSITORY.replace("/", "_")
    reject_symlinks(source)
    download_snapshot(port)
    return install_snapshot(source, destination)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8200, help="Local model-download service port")
    args = parser.parse_args()
    try:
        installed = download_model(Path(__file__).resolve().parent / "models", args.port)
    except (OSError, ValueError, RuntimeError, http.client.HTTPException) as error:
        raise SystemExit(
            f"Detector preparation failed: {error}\n"
            "Use scripts/download_llm_model.sh --use-case pipeline-defect-detection "
            "--detector-only to start the model-download service."
        ) from error
    print(f"Verified detector and notices: {installed}")
