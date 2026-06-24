"""Tests for verify_builds.py."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import verify_builds
from verify_builds import check_docker, get_docker_cmd, main, verify_module_lang


class TestCheckDocker:
    @patch("subprocess.run")
    def test_docker_installed_and_running(self, mock_run: MagicMock):
        mock_run.return_value = MagicMock(returncode=0)
        assert check_docker() is True

    @patch("subprocess.run", side_effect=FileNotFoundError)
    def test_docker_not_installed(self, mock_run: MagicMock):
        assert check_docker() is False

    @patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "docker"))
    def test_docker_error(self, mock_run: MagicMock):
        assert check_docker() is False


class TestGetDockerCmd:
    def test_cmd_formatting(self):
        cmd = get_docker_cmd("some-image", "some/path", "run command")
        assert "docker" in cmd
        assert "run" in cmd
        assert "--rm" in cmd
        assert "-w" in cmd
        assert "/workspace/some/path" in cmd
        assert "some-image" in cmd
        assert "run" in cmd
        assert "command" in cmd


class TestVerifyModuleLang:
    @patch("subprocess.run")
    def test_verify_java_success(self, mock_run: MagicMock, tmp_path: Path):
        # Create output dir dummy so verification isn't skipped
        out_dir = tmp_path / "target" / "generated-sources" / "gc" / "java"
        out_dir.mkdir(parents=True)
        
        with patch("verify_builds.ROOT", tmp_path), \
             patch("verify_builds.OUTPUT", tmp_path / "target" / "generated-sources"):
            mock_run.return_value = MagicMock(returncode=0)
            res = verify_module_lang("gc", "java", dry_run=False)
            assert res is True
            assert mock_run.call_count == 1

    @patch("subprocess.run")
    def test_verify_python_success(self, mock_run: MagicMock, tmp_path: Path):
        # Create output dir dummy
        out_dir = tmp_path / "target" / "generated-sources" / "gc" / "python"
        out_dir.mkdir(parents=True)
        
        with patch("verify_builds.ROOT", tmp_path), \
             patch("verify_builds.OUTPUT", tmp_path / "target" / "generated-sources"):
            mock_run.return_value = MagicMock(returncode=0)
            res = verify_module_lang("gc", "python", dry_run=False)
            assert res is True
            assert mock_run.call_count == 1

    def test_verify_skipped_when_output_dir_missing(self, tmp_path: Path):
        # No target directory created
        with patch("verify_builds.ROOT", tmp_path), \
             patch("verify_builds.OUTPUT", tmp_path / "target" / "generated-sources"):
            res = verify_module_lang("gc", "java", dry_run=False)
            assert res is True  # skipped returns True


class TestVerifyBuildsMain:
    @patch("verify_builds.check_docker", return_value=True)
    @patch("verify_builds.verify_module_lang", return_value=True)
    def test_main_success(self, mock_verify: MagicMock, mock_check: MagicMock):
        rc = main(["--specs", "gc", "--langs", "java", "--dry-run"])
        assert rc == 0

    @patch("verify_builds.check_docker", return_value=False)
    def test_main_no_docker_fails(self, mock_check: MagicMock):
        rc = main(["--specs", "gc", "--langs", "java"])
        assert rc == 1
