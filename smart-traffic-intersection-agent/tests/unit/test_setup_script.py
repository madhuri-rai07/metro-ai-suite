# SPDX-FileCopyrightText: (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
"""Tests for setup script defaults without deploying services."""

import json
import os
import subprocess
from pathlib import Path

import pytest

SETUP_SCRIPT = Path(__file__).resolve().parents[2] / "setup.sh"


def run_setup(command, env=None, args=(), expected_returncode=0):
    test_env = {"PATH": os.defpath, "VLM_MODEL_NAME": "test/model", **(env or {})}
    result = subprocess.run(
        [
            "bash",
            "--noprofile",
            "--norc",
            "-c",
            'source "$1" --setenv >/dev/null && ' + command,
            "bash",
            str(SETUP_SCRIPT),
            *map(str, args),
        ],
        env={key: value for key, value in test_env.items() if value is not None},
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == expected_returncode, result.stderr
    return result


@pytest.mark.parametrize(
    "model",
    [
        "OpenVINO/Phi-3.5-vision-instruct-int8-ov",
        "OpenVINO/Qwen2-VL-2B-Instruct-int4-ov",
    ],
)
def test_setup_exports_selected_model(model):
    result = run_setup("printenv VLM_MODEL_NAME", {"VLM_MODEL_NAME": model})
    assert result.stdout.strip() == model


@pytest.mark.parametrize("model", [None, ""])
def test_setup_requires_explicit_model_selection(model):
    result = run_setup(
        "printenv VLM_MODEL_NAME",
        {"VLM_MODEL_NAME": model},
        expected_returncode=1,
    )
    assert "VLM_MODEL_NAME is required" in result.stderr


@pytest.mark.parametrize(
    ("vendors", "render_device", "expected"),
    [
        ([], True, "CPU"),
        (["0x8086"], True, "GPU"),
        (["0x1002"], True, "CPU"),
        (["0x1002", "0x8086"], True, "GPU"),
        (["0x8086"], False, "CPU"),
    ],
)
def test_detect_vlm_target_device(tmp_path, vendors, render_device, expected):
    dri = tmp_path / "dri"
    drm = tmp_path / "drm"
    dri.mkdir()
    drm.mkdir()
    for index, vendor in enumerate(vendors, start=128):
        name = f"renderD{index}"
        device = drm / name / "device"
        device.mkdir(parents=True)
        (device / "vendor").write_text(vendor + "\n")
        if render_device:
            (dri / name).symlink_to("/dev/null")

    result = run_setup(
        'detect_vlm_target_device "$2" "$3"',
        {"VLM_TARGET_DEVICE": "CPU"},
        (dri, drm),
    )
    assert result.stdout.strip() == expected


@pytest.mark.parametrize(
    ("device", "si_device", "image_tag", "expected_si"),
    [
        ("CPU", "GPU", "2026.4.0", "GPU"),
        ("GPU", "GPU", "2026.4.0-gpu", "CPU"),
        ("GPU", "NPU", "2026.4.0-gpu", "CPU"),
    ],
)
def test_device_override_configures_ovms_and_si(
    device, si_device, image_tag, expected_si
):
    result = run_setup(
        "printenv VLM_TARGET_DEVICE OVMS_TAG TC_SI_TARGET_DEVICE",
        {"VLM_TARGET_DEVICE": device, "TC_SI_TARGET_DEVICE": si_device},
    )
    assert result.stdout.splitlines() == [device, image_tag, expected_si]


@pytest.mark.parametrize("device", [None, ""])
def test_setup_automatically_selects_host_device(device):
    env = {}
    if device is not None:
        env["VLM_TARGET_DEVICE"] = device
    result = run_setup(
        "printenv VLM_TARGET_DEVICE OVMS_TAG; detect_vlm_target_device /dev/dri /sys/class/drm",
        env,
    )
    selected, image_tag, detected = result.stdout.splitlines()
    assert selected == detected
    assert image_tag == ("2026.4.0-gpu" if detected == "GPU" else "2026.4.0")


@pytest.mark.parametrize(
    ("fetch_status", "download_status", "with_log"),
    [(22, 0, False), (0, 23, True), (0, 23, False), (0, 0, False)],
)
def test_model_preparation_diagnostics(
    tmp_path, fetch_status, download_status, with_log
):
    helper = tmp_path / "helper.sh"
    helper.write_text(
        "#!/bin/bash\n"
        "# SPDX-FileCopyrightText: (C) 2026 Intel Corporation\n"
        "# SPDX-License-Identifier: Apache-2.0\n"
        "set -euo pipefail\n"
        "echo 'Downloader progress'\n"
        "echo 'Downloader stderr' >&2\n"
        f"exit {download_status}\n"
    )
    models = tmp_path / ".ovms/models"
    generated = models / "openvino_models/cpu/int8/config_all.json"
    generated.parent.mkdir(parents=True)
    generated.write_text(
        json.dumps(
            {
                "model_config_list": [
                    {"config": {"name": "test/model", "base_path": "test/model"}}
                ]
            }
        )
    )
    if with_log:
        log_dir = tmp_path / ".model_download_logs"
        log_dir.mkdir()
        (log_dir / "model_download_test.log").write_text("Download failure details\n")

    failed = bool(fetch_status or download_status)
    command = (
        'cd "$2" && export OVMS_CONFIG_DIR="$PWD/.ovms"; '
        + (
            f"curl() {{ return {fetch_status}; }}; "
            if fetch_status
            else 'curl() { cp "$PWD/helper.sh" "$4"; }; '
        )
        + 'prepare_ovms_model && printf "MODEL=<%s>\\n" "$VLM_STORAGE_MODEL_NAME"'
    )
    result = run_setup(
        command,
        env={"VLM_TARGET_DEVICE": "CPU"},
        args=(tmp_path,),
        expected_returncode=1 if failed else 0,
    )
    assert "Checking for model:" in result.stderr
    assert "Fetching get_model.sh" in result.stderr
    if fetch_status:
        assert "ERROR: Failed to download get_model.sh" in result.stderr
        assert "Downloader progress" not in result.stderr
    else:
        assert "Downloader progress" in result.stderr
        assert "Downloader stderr" in result.stderr
        assert "Downloader progress" not in result.stdout
        if download_status:
            assert "exit code: 23" in result.stderr
            if with_log:
                assert "Last 30 lines from log:" in result.stderr
                assert "Download failure details" in result.stderr
            else:
                assert "No model download log found in:" in result.stderr
        else:
            assert "Created config.json" in result.stderr
            assert "MODEL=<test/model>\n" in result.stdout
    if failed:
        assert "MODEL=<" not in result.stdout


def test_cached_model_keeps_diagnostics_out_of_model_name(tmp_path):
    models = tmp_path / "models"
    models.mkdir()
    (models / "config.json").write_text(
        json.dumps({"model_config_list": [{"config": {"name": "test/model"}}]})
    )
    result = run_setup(
        'export OVMS_CONFIG_DIR="$2"; '
        'prepare_ovms_model && printf "MODEL=<%s>\\n" "$VLM_STORAGE_MODEL_NAME"',
        env={"VLM_TARGET_DEVICE": "CPU"},
        args=(tmp_path,),
    )
    assert "Skipping export." in result.stderr
    assert "MODEL=<test/model>\n" in result.stdout


def git(*args):
    return subprocess.run(
        ["git", *map(str, args)],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
        env={
            **os.environ,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "/dev/null",
        },
    )


@pytest.fixture
def dependency_repo(tmp_path):
    def create(subdir):
        repo = tmp_path / "upstream"
        git("init", "--initial-branch=release-test", repo)
        install = repo / subdir / "smart-intersection/install.sh"
        install.parent.mkdir(parents=True)
        install.write_text("#!/bin/sh\nexit 23\n")
        install.chmod(0o755)
        git("-C", repo, "add", ".")
        git(
            "-C",
            repo,
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "-c",
            "core.hooksPath=/dev/null",
            "commit",
            "-m",
            "Dependency fixture",
        )
        return repo

    return create


@pytest.mark.parametrize(
    "subdir",
    ["metro-vision-ai-app-recipe", "metro-ai-suite/metro-vision-ai-app-recipe"],
)
@pytest.mark.parametrize("existing", [False, True])
def test_dependency_checkout_supports_layouts_and_retries(
    tmp_path, dependency_repo, subdir, existing
):
    repo = dependency_repo(subdir)
    clone = tmp_path / "dependency clone"
    if existing:
        git("clone", "--sparse", repo, clone)
        git("-C", clone, "sparse-checkout", "set", "wrong-layout")
        (clone / "keep.txt").write_text("local data")

    result = run_setup(
        'CLONE_PATH="$2"; SI_SETUP_REPO_URL="$3"; SI_SETUP_BRANCH=release-test; '
        "prepare_dependency_checkout && prepare_dependency_checkout && "
        'printf "RI_DIR=%s\\n" "$RI_DIR"',
        args=(clone, repo),
    )
    assert f"RI_DIR={clone}/{subdir}/smart-intersection" in result.stdout
    assert (clone / subdir / "smart-intersection/install.sh").is_file()
    if existing:
        assert (clone / "keep.txt").read_text() == "local data"
        assert "Cloning repository" not in result.stdout

    install = clone / subdir / "smart-intersection/install.sh"
    install.write_text("#!/bin/sh\nexit 42\n")
    run_setup('CLONE_PATH="$2"; prepare_dependency_checkout', args=(clone,))
    assert install.read_text() == "#!/bin/sh\nexit 42\n"


def test_dependency_clone_failure_stops_before_sparse_checkout(
    tmp_path, dependency_repo
):
    repo = dependency_repo("metro-vision-ai-app-recipe")
    result = run_setup(
        'CLONE_PATH="$2"; SI_SETUP_REPO_URL="$3"; SI_SETUP_BRANCH=missing; '
        "prepare_dependency_checkout",
        args=(tmp_path / "clone", repo),
        expected_returncode=1,
    )
    assert "Failed to clone dependencies" in result.stdout
    assert "cannot change to" not in result.stderr


def test_dependency_checkout_preserves_non_repository_directory(tmp_path):
    clone = tmp_path / "clone"
    clone.mkdir()
    marker = clone / "keep.txt"
    marker.write_text("local data")
    result = run_setup(
        'CLONE_PATH="$2"; SI_SETUP_REPO_URL="$2"; prepare_dependency_checkout',
        args=(clone,),
        expected_returncode=1,
    )
    assert "Failed to clone dependencies" in result.stdout
    assert marker.read_text() == "local data"


def test_dependency_checkout_rejects_unsupported_layout(tmp_path, dependency_repo):
    repo = dependency_repo("unsupported")
    result = run_setup(
        'CLONE_PATH="$2"; prepare_dependency_checkout',
        args=(repo,),
        expected_returncode=1,
    )
    assert "supported layout" in result.stdout


def test_dependency_sparse_failure_is_reported(tmp_path, dependency_repo):
    repo = dependency_repo("metro-vision-ai-app-recipe")
    clone = tmp_path / "clone"
    git("clone", "--sparse", repo, clone)
    result = run_setup(
        'CLONE_PATH="$2"; '
        'git() { if [ "$3" = sparse-checkout ]; then return 1; fi; command git "$@"; }; '
        "prepare_dependency_checkout",
        args=(clone,),
        expected_returncode=1,
    )
    assert "Failed to populate dependency checkout" in result.stdout
    assert not (
        clone / "metro-vision-ai-app-recipe/smart-intersection/install.sh"
    ).exists()


def test_dependency_install_failure_preserves_working_directory(dependency_repo):
    repo = dependency_repo("metro-vision-ai-app-recipe")
    result = run_setup(
        'CLONE_PATH="$2"; before="$PWD"; '
        "check_and_setup_dependencies; status=$?; "
        '[ "$status" -eq 1 ] && [ "$PWD" = "$before" ]',
        args=(repo,),
    )
    assert "Failed to run install.sh" in result.stdout
