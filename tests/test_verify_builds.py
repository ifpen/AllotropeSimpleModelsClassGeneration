"""Tests for verify_builds.py."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from verify_builds import main, verify_module_lang, verify_modules


class TestVerifyModuleLang:
    @patch("subprocess.run")
    def test_verify_java_success(self, mock_run: MagicMock, tmp_path: Path):
        out_dir = tmp_path / "target" / "generated-sources" / "gc" / "java"
        out_dir.mkdir(parents=True)
        (out_dir / "pom.xml").touch()
        
        with patch("verify_builds.ROOT", tmp_path), \
             patch("verify_builds.OUTPUT", tmp_path / "target" / "generated-sources"):
            mock_run.return_value = MagicMock(returncode=0)
            res = verify_module_lang("gc", "java", dry_run=False)
            assert res is True
            assert mock_run.call_count == 1
            assert mock_run.call_args.args[0] == ("mvn", "--batch-mode", "-DskipTests", "compile")
            assert mock_run.call_args.kwargs["cwd"] == out_dir

    @patch("subprocess.run")
    def test_verify_python_success(self, mock_run: MagicMock, tmp_path: Path):
        out_dir = tmp_path / "target" / "generated-sources" / "gc" / "python"
        out_dir.mkdir(parents=True)
        (out_dir / "pyproject.toml").touch()
        
        with patch("verify_builds.ROOT", tmp_path), \
             patch("verify_builds.OUTPUT", tmp_path / "target" / "generated-sources"):
            mock_run.return_value = MagicMock(returncode=0)
            res = verify_module_lang("gc", "python", dry_run=False)
            assert res is True
            assert mock_run.call_count == 1

    def test_verify_fails_when_output_dir_missing(self, tmp_path: Path):
        with patch("verify_builds.ROOT", tmp_path), \
             patch("verify_builds.OUTPUT", tmp_path / "target" / "generated-sources"):
            res = verify_module_lang("gc", "java", dry_run=False)
            assert res is False

    def test_verify_fails_when_manifest_missing(self, tmp_path: Path):
        out_dir = tmp_path / "target" / "generated-sources" / "gc" / "java"
        out_dir.mkdir(parents=True)
        with patch("verify_builds.OUTPUT", tmp_path / "target" / "generated-sources"):
            assert verify_module_lang("gc", "java") is False

    @patch("subprocess.run", side_effect=OSError("mvn unavailable"))
    def test_verify_fails_when_build_tool_missing(self, mock_run: MagicMock, tmp_path: Path):
        out_dir = tmp_path / "target" / "generated-sources" / "gc" / "java"
        out_dir.mkdir(parents=True)
        (out_dir / "pom.xml").touch()
        with patch("verify_builds.OUTPUT", tmp_path / "target" / "generated-sources"):
            assert verify_module_lang("gc", "java") is False

    @patch("subprocess.run")
    def test_typescript_runs_actual_package_build(self, mock_run: MagicMock, tmp_path: Path):
        out_dir = tmp_path / "target" / "generated-sources" / "gc" / "typescript"
        out_dir.mkdir(parents=True)
        (out_dir / "package.json").write_text('{"scripts":{"build":"ng-packagr"}}')
        mock_run.return_value = MagicMock(returncode=0)
        with patch("verify_builds.OUTPUT", tmp_path / "target" / "generated-sources"):
            assert verify_module_lang("gc", "typescript-angular") is True
        assert [call.args[0] for call in mock_run.call_args_list] == [
            ("npm", "install", "--ignore-scripts"),
            ("npm", "run", "build"),
        ]

    @patch("subprocess.run", return_value=MagicMock(returncode=1))
    def test_typescript_does_not_build_if_install_fails(self, mock_run: MagicMock, tmp_path: Path):
        out_dir = tmp_path / "target" / "generated-sources" / "gc" / "typescript"
        out_dir.mkdir(parents=True)
        (out_dir / "package.json").write_text('{"scripts":{"build":"ng-packagr"}}')
        with patch("verify_builds.OUTPUT", tmp_path / "target" / "generated-sources"):
            assert verify_module_lang("gc", "typescript-angular") is False
        mock_run.assert_called_once()

    @patch("verify_builds.verify_module_lang", side_effect=[True, False])
    def test_verify_modules_checks_all_pairs(self, mock_verify: MagicMock):
        assert verify_modules(["commons", "gc"], ["java"]) is False
        assert mock_verify.call_count == 2


class TestVerifyBuildsMain:
    @patch("verify_builds.verify_modules", return_value=True)
    def test_main_success(self, mock_verify: MagicMock):
        rc = main(["--specs", "gc", "--langs", "java", "--dry-run"])
        assert rc == 0
        mock_verify.assert_called_once_with(["gc"], ["java"], dry_run=True)

    @patch("verify_builds.verify_modules", return_value=False)
    def test_main_build_failure_returns_error(self, mock_verify: MagicMock):
        rc = main(["--specs", "gc", "--langs", "java"])
        assert rc == 1

    def test_main_rejects_unknown_module(self, capsys: pytest.CaptureFixture[str]):
        assert main(["--specs", "typo", "--dry-run"]) == 1
        assert "Unknown module" in capsys.readouterr().err
