# SPDX-FileCopyrightText: (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

"""Regression tests for service-based detector downloads and verified installation."""

import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location(
    "download_model", Path(__file__).resolve().parents[1] / "download_model.py"
)
downloader = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(downloader)


class DownloadModelTests(unittest.TestCase):
    """Keep the deployed cache isolated from service failures or invalid artifacts."""

    def setUp(self):
        self.temporary = self.enterContext(tempfile.TemporaryDirectory())
        self.models = Path(self.temporary) / "models"
        self.source = (self.models / downloader.SERVICE_DOWNLOAD_PATH / "huggingface"
                       / downloader.REPOSITORY.replace("/", "_"))
        self.payloads = {"model.xml": b"xml-content", "model.bin": b"bin-content",
                         "DATASET_ATTRIBUTION.txt": b"notice"}
        artifacts = {name: (len(data), hashlib.sha256(data).hexdigest())
                     for name, data in self.payloads.items()}
        self.enterContext(patch.object(downloader, "ARTIFACTS", artifacts))
        self.enterContext(patch.object(downloader.time, "sleep"))

    def job(self, status):
        """Return the service's model identity and job state."""
        return {"model_name": downloader.REPOSITORY, "hub": "huggingface", "status": status}

    def response(self, port, path, body=None):
        """Simulate the service writing the requested snapshot to the shared volume."""
        self.assertEqual(port, 8200)
        self.assertFalse((self.models / "hf" / downloader.REVISION).exists())
        if body is not None:
            self.assertEqual(
                path, f"models/download?download_path={downloader.SERVICE_DOWNLOAD_PATH}"
            )
            self.assertEqual(body, {
                "models": [{
                    "name": downloader.REPOSITORY, "hub": "huggingface",
                    "revision": downloader.REVISION, "is_ovms": False,
                }],
                "parallel_downloads": False,
            })
            return {"job_ids": ["download-test"]}
        self.assertEqual(path, "jobs/download-test")
        self.source.mkdir(parents=True, exist_ok=True)
        for name, content in self.payloads.items():
            (self.source / name).write_bytes(content)
        return self.job("completed")

    def test_complete_install_includes_notices_and_reuses_verified_cache(self):
        """Use only the service for a missing model; reuse an intact cache offline."""
        old_model = self.models / "pipeline-defect-detection.xml"
        self.models.mkdir()
        old_model.write_bytes(b"existing-user-model")
        with patch.object(downloader, "service_request", side_effect=self.response) as fetch:
            target = downloader.download_model(self.models)
            self.assertEqual(fetch.call_count, 2)
        with patch.object(downloader, "service_request", side_effect=AssertionError("network")):
            self.assertEqual(downloader.download_model(self.models), target)
        for name, data in self.payloads.items():
            self.assertEqual((target / name).read_bytes(), data)
        self.assertEqual(old_model.read_bytes(), b"existing-user-model")

    def test_bad_hash_truncation_oversize_and_missing_notice_are_not_installed(self):
        """A successful service job is not sufficient evidence of artifact integrity."""
        for payload in [b"bad-content", b"x", b"x" * 100, None]:
            with self.subTest(payload=payload):
                if payload is None:
                    self.payloads.pop("DATASET_ATTRIBUTION.txt")
                    (self.source / "DATASET_ATTRIBUTION.txt").unlink()
                    self.payloads["model.bin"] = b"bin-content"
                else:
                    self.payloads["model.bin"] = payload
                with patch.object(downloader, "service_request", side_effect=self.response):
                    with self.assertRaises(ValueError):
                        downloader.download_model(self.models)
                self.assertEqual(list((self.models / "hf").iterdir()), [])

    def test_pending_job_is_polled_before_installation(self):
        """Never publish files while the service is still downloading."""
        calls = 0

        def delayed(port, path, body=None):
            nonlocal calls
            calls += 1
            if calls == 2:
                return self.job("downloading")
            return self.response(port, path, body)

        with patch.object(downloader, "service_request", side_effect=delayed):
            self.assertTrue(downloader.download_model(self.models).is_dir())
        self.assertEqual(calls, 3)

    def test_service_errors_and_unknown_states_leave_no_installed_revision(self):
        """Do not treat failures, canceled jobs, lost connections or invalid states as success."""
        responses = [
            ConnectionError("service unavailable"),
            self.job("failed"),
            self.job("canceled"),
            self.job("unexpected"),
            {**self.job("completed"), "model_name": "another-model"},
        ]
        for response in responses:
            with self.subTest(response=response):
                with patch.object(downloader, "service_request", side_effect=[
                    {"job_ids": ["download-test"]}, response,
                ]):
                    with self.assertRaises((OSError, RuntimeError, ValueError)):
                        downloader.download_model(self.models)
                self.assertEqual(list((self.models / "hf").iterdir()), [])

    def test_timeout_and_invalid_job_ids_do_not_publish_a_model(self):
        """Bound waiting and reject job IDs before including them in API paths."""
        with patch.object(downloader, "DOWNLOAD_TIMEOUT", 0):
            with patch.object(downloader, "service_request", return_value={
                "job_ids": ["download-test"],
            }):
                with self.assertRaises(TimeoutError):
                    downloader.download_model(self.models)
        for jobs in ([], ["one", "two"], ["../other"], [None]):
            with self.subTest(jobs=jobs):
                with patch.object(downloader, "service_request", return_value={"job_ids": jobs}):
                    with self.assertRaisesRegex(ValueError, "job ID"):
                        downloader.download_model(self.models)
        self.assertEqual(list((self.models / "hf").iterdir()), [])

    def test_corrupted_existing_cache_is_not_silently_trusted_or_overwritten(self):
        """Preserve corrupt installed files for diagnosis instead of replacing them."""
        with patch.object(downloader, "service_request", side_effect=self.response):
            target = downloader.download_model(self.models)
        (target / "model.bin").write_bytes(b"BAD-content")
        with patch.object(downloader, "service_request", side_effect=AssertionError("network")):
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                downloader.download_model(self.models)
        self.assertEqual((target / "model.bin").read_bytes(), b"BAD-content")

    def test_symlinked_revision_or_service_snapshot_is_rejected(self):
        """Reject redirected cache paths before submitting any service request."""
        cache = self.models / "hf"
        cache.mkdir(parents=True)
        target = cache / downloader.REVISION
        elsewhere = Path(self.temporary) / "elsewhere"
        elsewhere.mkdir()
        target.symlink_to(elsewhere, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlink"):
            downloader.download_model(self.models)
        target.unlink()
        self.source.parent.mkdir(parents=True)
        self.source.symlink_to(elsewhere, target_is_directory=True)
        with patch.object(downloader, "service_request", side_effect=AssertionError("network")):
            with self.assertRaisesRegex(ValueError, "symlink"):
                downloader.download_model(self.models)

    def test_symlinked_artifact_and_copy_failure_do_not_publish_a_model(self):
        """Check source files and clean incomplete local installation directories."""
        self.response(8200, "jobs/download-test")
        destination = self.models / "hf" / downloader.REVISION
        destination.parent.mkdir()
        original = self.source / "model.xml"
        original.rename(self.source / "original.xml")
        original.symlink_to(self.source / "original.xml")
        with self.assertRaisesRegex(ValueError, "invalid"):
            downloader.install_snapshot(self.source, destination)
        original.unlink()
        original.write_bytes(self.payloads["model.xml"])
        with patch.object(downloader.shutil, "copyfile", side_effect=OSError("copy failed")):
            with self.assertRaises(OSError):
                downloader.install_snapshot(self.source, destination)
        self.assertEqual(list(destination.parent.iterdir()), [])

    def test_service_client_posts_json_and_rejects_http_errors(self):
        """Exercise the real local HTTP client without reaching Hugging Face."""
        requests = []

        class Handler(BaseHTTPRequestHandler):
            """Record requests from the loopback-only client."""

            def do_POST(self):  # pylint: disable=invalid-name
                """Return a job response to a JSON request."""
                body = self.rfile.read(int(self.headers["Content-Length"]))
                requests.append((self.path, json.loads(body)))
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'{"job_ids": ["test"]}')

            def do_GET(self):  # pylint: disable=invalid-name
                """Return an HTTP error that must not be interpreted as a job."""
                self.send_response(503)
                self.end_headers()

            def log_message(self, *_args):
                pass

        with HTTPServer(("127.0.0.1", 0), Handler) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                result = downloader.service_request(server.server_port, "models/download", {"a": 1})
                self.assertEqual(result, {"job_ids": ["test"]})
                self.assertEqual(requests, [("/api/v1/models/download", {"a": 1})])
                with self.assertRaisesRegex(RuntimeError, "HTTP 503"):
                    downloader.service_request(server.server_port, "jobs/test")
            finally:
                server.shutdown()
                thread.join(timeout=5)

    def test_detector_only_entrypoint_uses_service_without_llm_or_generic_yolo(self):
        """Exercise shell routing without Docker mutations or environment-file updates."""
        root = Path(self.temporary) / "project"
        scripts = root / "scripts"
        app = root / "apps/pipeline-defect-detection"
        tools = root / "bin"
        for directory in (scripts, app, tools):
            directory.mkdir(parents=True)
        script = scripts / "download_llm_model.sh"
        component = Path(__file__).resolve().parents[3]
        shutil.copyfile(component / "scripts/download_llm_model.sh", script)
        environment = app / ".env_pipeline-defect-detection"
        environment.write_text("LLM_MODE=llm\nMODEL_DOWNLOAD_PORT=8234\n")
        log = root / "calls"
        programs = {
            "docker": (
                '#!/bin/sh\n'
                'test "${USE_CASE:-}" = "pipeline-defect-detection" || exit 98\n'
                'printf "docker %s\\n" "$*" >> "$CALL_LOG"\n'
            ),
            "curl": (
                '#!/bin/sh\ncase "$*" in\n'
                '  *"/api/v1/models/results") printf "{}";;\n'
                '  *) exit 99;;\nesac\n'
            ),
            "python3.12": '#!/bin/sh\nprintf "python %s\\n" "$*" >> "$CALL_LOG"\n',
        }
        for name, content in programs.items():
            path = tools / name
            path.write_text(content)
            path.chmod(0o755)
        result = subprocess.run(
            ["bash", str(script), "--use-case", "pipeline-defect-detection", "--detector-only"],
            env={
                **{key: value for key, value in os.environ.items() if key != "USE_CASE"},
                "PATH": f"{tools}:{os.environ['PATH']}", "CALL_LOG": str(log),
            },
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = log.read_text().splitlines()
        self.assertEqual(len(calls), 2)
        self.assertTrue(calls[0].endswith("up -d model-download"))
        self.assertEqual(calls[1], f"python {app}/download_model.py --port 8234")
        self.assertEqual(environment.read_text(), "LLM_MODE=llm\nMODEL_DOWNLOAD_PORT=8234\n")


if __name__ == "__main__":
    unittest.main()
