# SPDX-FileCopyrightText: (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

"""Regression tests for the pinned detector installation, without network access."""

import hashlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError
from urllib.request import Request


SPEC = importlib.util.spec_from_file_location(
    "download_model", Path(__file__).resolve().parents[1] / "download_model.py"
)
downloader = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(downloader)


class DownloadModelTests(unittest.TestCase):
    """Exercise integrity failures and installation without network access."""

    def setUp(self):
        self.temporary = self.enterContext(tempfile.TemporaryDirectory())
        self.models = Path(self.temporary) / "models"
        self.payloads = {"model.xml": b"xml-content", "model.bin": b"bin-content",
                         "DATASET_ATTRIBUTION.txt": b"notice"}
        artifacts = {name: (len(data), hashlib.sha256(data).hexdigest())
                     for name, data in self.payloads.items()}
        patched = patch.object(downloader, "ARTIFACTS", artifacts)
        patched.start()
        self.addCleanup(patched.stop)

    def response(self, url, timeout):
        """Return fixture bytes only for the pinned HTTPS artifact URLs."""
        self.assertEqual(timeout, 60)
        self.assertIn(f"/resolve/{downloader.REVISION}/", url)
        self.assertTrue(url.startswith("https://huggingface.co/"))
        self.assertFalse((self.models / "hf" / downloader.REVISION).exists())
        return io.BytesIO(self.payloads[url.rsplit("/", 1)[-1]])

    def test_complete_install_includes_notices_and_reuses_verified_cache(self):
        """Installation retains notices and does not replace legacy files."""
        old_model = self.models / "pipeline-defect-detection.xml"
        self.models.mkdir()
        old_model.write_bytes(b"existing-user-model")
        with patch.object(downloader.OPENER, "open", side_effect=self.response) as fetch:
            target = downloader.download_model(self.models)
            self.assertEqual(fetch.call_count, len(self.payloads))
        with patch.object(downloader.OPENER, "open", side_effect=AssertionError("network")):
            self.assertEqual(downloader.download_model(self.models), target)
        for name, data in self.payloads.items():
            self.assertEqual((target / name).read_bytes(), data)
        self.assertEqual(old_model.read_bytes(), b"existing-user-model")

    def test_bad_hash_truncation_and_oversize_never_install_a_partial_revision(self):
        """Unexpected payloads leave no partially usable model revision."""
        for payload in [b"bad-content", b"x", b"x" * 100]:
            with self.subTest(payload=payload):
                with patch.object(downloader.OPENER, "open", return_value=io.BytesIO(payload)):
                    with self.assertRaises(ValueError):
                        downloader.download_model(self.models)
                self.assertEqual(list((self.models / "hf").iterdir()), [])

    def test_network_failure_cleans_staging_and_keeps_model_uninstalled(self):
        """A failure after the first artifact also cleans staging."""
        responses = [io.BytesIO(self.payloads["model.xml"]), URLError("offline")]
        with patch.object(downloader.OPENER, "open", side_effect=responses):
            with self.assertRaises(URLError):
                downloader.download_model(self.models)
        self.assertEqual(list((self.models / "hf").iterdir()), [])

    def test_corrupted_existing_cache_is_not_silently_trusted_or_overwritten(self):
        """Corrupt cached files fail closed and remain available for diagnosis."""
        with patch.object(downloader.OPENER, "open", side_effect=self.response):
            target = downloader.download_model(self.models)
        (target / "model.bin").write_bytes(b"BAD-content")
        with patch.object(downloader.OPENER, "open", side_effect=AssertionError("network")):
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                downloader.download_model(self.models)
        self.assertEqual((target / "model.bin").read_bytes(), b"BAD-content")

    def test_symlinked_revision_or_artifact_is_rejected(self):
        """Do not follow redirected cache artifacts."""
        cache = self.models / "hf"
        cache.mkdir(parents=True)
        target = cache / downloader.REVISION
        elsewhere = Path(self.temporary) / "elsewhere"
        elsewhere.mkdir()
        target.symlink_to(elsewhere, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlink"):
            downloader.download_model(self.models)
        target.unlink()
        with patch.object(downloader.OPENER, "open", side_effect=self.response):
            downloader.download_model(self.models)
        original = target / "model.xml"
        original.rename(elsewhere / "model.xml")
        original.symlink_to(elsewhere / "model.xml")
        with self.assertRaisesRegex(ValueError, "invalid"):
            downloader.download_model(self.models)

    def test_only_https_redirects_are_allowed(self):
        """CDN redirects work, but HTTP downgrades and file URLs do not."""
        handler = downloader.HTTPSRedirectHandler()
        request = Request("https://huggingface.co/model")
        redirected = handler.redirect_request(
            request, None, 302, "Found", {}, "https://cdn.example.com/model"
        )
        self.assertEqual(redirected.full_url, "https://cdn.example.com/model")
        for target in ["http://cdn.example.com/model", "file:///tmp/model"]:
            with self.subTest(target=target), self.assertRaisesRegex(ValueError, "HTTPS"):
                handler.redirect_request(request, None, 302, "Found", {}, target)


if __name__ == "__main__":
    unittest.main()
