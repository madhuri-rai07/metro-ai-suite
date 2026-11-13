# SPDX-FileCopyrightText: (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

"""Exercise dataset HTTP responses with real curl and an isolated local server."""

from contextlib import redirect_stdout
from http.server import BaseHTTPRequestHandler, HTTPServer
import importlib.util
import io
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import zipfile


SPEC = importlib.util.spec_from_file_location(
    "download_and_prep_data", Path(__file__).resolve().parents[1] / "download_and_prep_data.py"
)
PREP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PREP)


class DownloadDatasetTests(unittest.TestCase):
    """Reject HTTP failures and invalid bodies before declaring download success."""

    @classmethod
    def setUpClass(cls):
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as output:
            output.writestr("sample.txt", "dataset sample")
        responses = {
            "/archive": (200, archive.getvalue()),
            "/missing": (404, b""),
            "/unavailable": (503, b"<html>Service unavailable</html>"),
            "/empty": (200, b""),
            "/login": (200, b"<html>Sign in</html>"),
        }

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/redirect":
                    self.send_response(302)
                    self.send_header("Location", "/archive")
                    self.end_headers()
                    return
                status, body = responses[self.path]
                self.send_response(status)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_args):
                pass

        cls.server = HTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join(timeout=5)
        cls.server.server_close()

    def setUp(self):
        proxy_env = patch.dict("os.environ", {"NO_PROXY": "127.0.0.1", "no_proxy": "127.0.0.1"})
        proxy_env.start()
        self.addCleanup(proxy_env.stop)

    def test_http_errors_report_status_without_success_or_extraction(self):
        for path, status in (("/missing", 404), ("/unavailable", 503)):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as directory:
                output = io.StringIO()
                with redirect_stdout(output), self.assertRaises(SystemExit) as error:
                    PREP.download_dataset(self.base_url + path, Path(directory))
                self.assertEqual(error.exception.code, 1)
                self.assertIn(f"HTTP {status}", output.getvalue())
                self.assertNotIn("Download complete", output.getvalue())
                self.assertNotIn("Extracting dataset", output.getvalue())
                self.assertEqual(list(Path(directory).iterdir()), [])

    def test_empty_and_html_responses_are_not_successful_downloads(self):
        for path in ("/empty", "/login"):
            with self.subTest(path=path), tempfile.TemporaryDirectory() as directory:
                output = io.StringIO()
                with redirect_stdout(output), self.assertRaises(SystemExit) as error:
                    PREP.download_dataset(self.base_url + path, Path(directory))
                self.assertEqual(error.exception.code, 1)
                self.assertIn("not a valid zip archive", output.getvalue())
                self.assertNotIn("Download complete", output.getvalue())
                self.assertEqual(list(Path(directory).iterdir()), [])

    def test_redirected_archive_is_extracted_and_temporary_zip_removed(self):
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()):
            result = PREP.download_dataset(self.base_url + "/redirect", Path(directory))
            self.assertEqual(result, Path(directory))
            self.assertEqual((result / "sample.txt").read_text(), "dataset sample")
            self.assertFalse((result / "dataset.zip").exists())


if __name__ == "__main__":
    unittest.main()
