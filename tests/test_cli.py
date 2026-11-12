"""Tests for :mod:`allotrope_gen.cli`."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from unittest.mock import MagicMock, patch

from allotrope_gen.command import generator_cli
from allotrope_gen.cli import (
    _build_parser,
    _check_version,
    _resolve_java,
    _validate_args,
    check_prerequisites,
    main,
)
from allotrope_gen.config import LANGUAGES, SPECS


class TestCli:
    def test_build_parser_defaults(self):
        parser = _build_parser()
        args = parser.parse_args([])
        assert args.specs == list(SPECS)
        assert args.langs == list(LANGUAGES)
        assert args.dry_run is False
        assert args.no_clean is False
        assert args.commons_only is False
        assert args.no_verify_builds is False

    def test_validate_args_valid(self):
        parser = _build_parser()
        args = parser.parse_args(["--specs", "gc", "--langs", "java"])
        assert _validate_args(args) == 0

    def test_validate_args_invalid_spec(self, capsys: pytest.CaptureFixture[str]):
        parser = _build_parser()
        args = parser.parse_args(["--specs", "invalid_spec"])
        assert _validate_args(args) == 1
        captured = capsys.readouterr()
        assert "[ERROR] Unknown spec(s): ['invalid_spec']" in captured.err

    def test_validate_args_invalid_lang(self, capsys: pytest.CaptureFixture[str]):
        parser = _build_parser()
        args = parser.parse_args(["--langs", "invalid_lang"])
        assert _validate_args(args) == 1
        captured = capsys.readouterr()
        assert "[ERROR] Unknown language(s): ['invalid_lang']" in captured.err

    def test_list_specs(self, capsys: pytest.CaptureFixture[str]):
        with patch("allotrope_gen.cli.check_prerequisites") as mock_check:
            rc = main(["--list-specs"])
        assert rc == 0
        mock_check.assert_not_called()
        captured = capsys.readouterr()
        assert "gc" in captured.out

    def test_list_langs(self, capsys: pytest.CaptureFixture[str]):
        with patch("allotrope_gen.cli.check_prerequisites") as mock_check:
            rc = main(["--list-langs"])
        assert rc == 0
        mock_check.assert_not_called()
        captured = capsys.readouterr()
        assert "java" in captured.out
        assert "python" in captured.out

    def test_invalid_args_exits_early(self):
        with (
            patch("allotrope_gen.cli.generate_commons") as mock_commons,
            patch("allotrope_gen.cli.check_prerequisites") as mock_check,
        ):
            rc = main(["--specs", "invalid_spec"])
            assert rc == 1
            mock_commons.assert_not_called()
            mock_check.assert_not_called()

    def test_prerequisite_failure_prevents_generation(self):
        with (
            patch("allotrope_gen.cli.check_prerequisites", return_value=False),
            patch("allotrope_gen.cli.generate_commons") as mock_commons,
        ):
            assert main(["--specs", "gc"]) == 1
            mock_commons.assert_not_called()

    def test_prerequisite_check_allows_dry_run_without_external_tools(self):
        with (
            patch("allotrope_gen.cli.sys.version_info", (3, 12)),
            patch("allotrope_gen.cli.importlib.util.find_spec", return_value=object()),
            patch("allotrope_gen.cli.shutil.which") as mock_which,
        ):
            assert check_prerequisites(dry_run=True)
            mock_which.assert_not_called()

    def test_prerequisite_check_reports_missing_tools(self, capsys: pytest.CaptureFixture[str]):
        with (
            patch("allotrope_gen.cli.sys.version_info", (3, 12)),
            patch("allotrope_gen.cli.importlib.util.find_spec", return_value=object()),
            patch("allotrope_gen.cli.shutil.which", return_value=None),
            patch("allotrope_gen.cli._resolve_java", return_value=None),
        ):
            assert not check_prerequisites()
        captured = capsys.readouterr()
        assert "Node.js was not found" in captured.err
        assert "Java was not found" in captured.err
        assert f"{generator_cli()} was not found" in captured.err

    def test_check_version_enforces_minimum(self, capsys: pytest.CaptureFixture[str]):
        result = MagicMock(returncode=0, stdout="v18.19.0", stderr="")
        with patch("allotrope_gen.cli.subprocess.run", return_value=result):
            assert not _check_version(
                "Node.js", ["node", "--version"], r"v?(\d+(?:\.\d+)+)", (20,)
            )
        assert "Node.js 20 or newer is required" in capsys.readouterr().err

    def test_check_version_requires_pinned_generator_version(self):
        result = MagicMock(returncode=0, stdout="7.22.0", stderr="")
        with patch("allotrope_gen.cli.subprocess.run", return_value=result):
            assert not _check_version(
                "OpenAPI Generator CLI",
                ["openapi-generator-cli", "version"],
                r"(\d+(?:\.\d+)+)",
                (7, 23, 0),
                exact=True,
            )

    def test_resolve_java_adds_java_home_bin_to_path(self, tmp_path: Path):
        java_bin = tmp_path / "bin"
        java_bin.mkdir()
        java_exe = java_bin / "java.exe"
        java_exe.touch()
        original_path = os.environ.get("PATH", "")
        with (
            patch("allotrope_gen.cli.shutil.which", return_value=None),
            patch.dict(os.environ, {"JAVA_HOME": str(tmp_path), "PATH": original_path}),
            patch("allotrope_gen.cli.sys.platform", "win32"),
        ):
            assert _resolve_java() == str(java_exe)
            assert os.environ["PATH"].split(os.pathsep)[0] == str(java_bin)

    def test_resolve_java_reports_invalid_java_home(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]):
        with (
            patch("allotrope_gen.cli.shutil.which", return_value=None),
            patch.dict(os.environ, {"JAVA_HOME": str(tmp_path)}),
            patch("allotrope_gen.cli.sys.platform", "win32"),
        ):
            assert _resolve_java() is None
        assert "JAVA_HOME is set but Java was not found" in capsys.readouterr().err

    @patch("allotrope_gen.cli.check_prerequisites", return_value=True)
    @patch("allotrope_gen.cli.generate_commons", return_value=True)
    @patch("allotrope_gen.cli.generate_specs", return_value=True)
    def test_main_success(self, mock_specs: MagicMock, mock_commons: MagicMock, mock_check: MagicMock):
        rc = main(["--specs", "gc", "--langs", "java", "--dry-run"])
        assert rc == 0
        mock_commons.assert_called_once_with(["java"], dry_run=True, no_clean=False)
        mock_specs.assert_called_once_with(["gc"], ["java"], dry_run=True, no_clean=False)

    @patch("allotrope_gen.cli.check_prerequisites", return_value=True)
    @patch("allotrope_gen.cli.generate_commons", return_value=False)
    @patch("allotrope_gen.cli.generate_specs", return_value=True)
    def test_main_commons_failure(self, mock_specs: MagicMock, mock_commons: MagicMock, mock_check: MagicMock):
        rc = main([])
        assert rc == 1

    @patch("allotrope_gen.cli.check_prerequisites", return_value=True)
    @patch("allotrope_gen.cli.generate_commons", return_value=True)
    @patch("allotrope_gen.cli.generate_specs", return_value=False)
    def test_main_specs_failure(self, mock_specs: MagicMock, mock_commons: MagicMock, mock_check: MagicMock):
        rc = main([])
        assert rc == 1

    @patch("allotrope_gen.cli.check_prerequisites", return_value=True)
    @patch("allotrope_gen.cli.generate_commons", return_value=True)
    @patch("allotrope_gen.cli.generate_specs", return_value=True)
    def test_main_commons_only(self, mock_specs: MagicMock, mock_commons: MagicMock, mock_check: MagicMock):
        rc = main(["--commons-only", "--no-verify-builds"])
        assert rc == 0
        mock_commons.assert_called_once()
        mock_specs.assert_not_called()

    @patch("allotrope_gen.cli.check_prerequisites", return_value=True)
    @patch("allotrope_gen.cli.generate_commons", return_value=True)
    @patch("allotrope_gen.cli.generate_specs", return_value=True)
    @patch("allotrope_gen.cli.verify_generated_builds", return_value=True)
    def test_main_verifies_builds_by_default(
        self,
        mock_verify: MagicMock,
        mock_specs: MagicMock,
        mock_commons: MagicMock,
        mock_check: MagicMock,
    ):
        assert main(["--specs", "gc", "--langs", "java"]) == 0
        mock_verify.assert_called_once_with(["gc"], ["java"], commons_only=False)
