"""Tests for :mod:`allotrope_gen.pipeline`."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from allotrope_gen.pipeline import clean_output, generate_commons, generate_specs, run


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------


class TestRun:
    def test_dry_run_does_not_execute(self):
        with patch("subprocess.run") as mock_run:
            res = run(["some", "cmd"], dry_run=True)
            assert res is True
            mock_run.assert_not_called()

    def test_run_success(self):
        mock_result = MagicMock(returncode=0)
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            res = run(["some", "cmd"], dry_run=False)
            assert res is True
            mock_run.assert_called_once_with(["some", "cmd"], shell=(sys.platform == "win32"))

    def test_run_failure(self, capsys: pytest.CaptureFixture[str]):
        mock_result = MagicMock(returncode=42)
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            res = run(["some", "cmd"], dry_run=False)
            assert res is False
            captured = capsys.readouterr()
            assert "[ERROR] Process exited with code 42" in captured.err


# ---------------------------------------------------------------------------
# clean_output
# ---------------------------------------------------------------------------


class TestCleanOutput:
    def test_no_clean_does_nothing(self, tmp_path: Path):
        dir_path = tmp_path / "subdir"
        dir_path.mkdir()
        with patch("shutil.rmtree") as mock_rmtree:
            clean_output(dir_path, dry_run=False, no_clean=True)
            mock_rmtree.assert_not_called()
            assert dir_path.exists()

    def test_nonexistent_dir_does_nothing(self, tmp_path: Path):
        dir_path = tmp_path / "nonexistent"
        with patch("shutil.rmtree") as mock_rmtree:
            clean_output(dir_path, dry_run=False, no_clean=False)
            mock_rmtree.assert_not_called()

    def test_dry_run_does_not_remove(self, tmp_path: Path):
        dir_path = tmp_path / "subdir"
        dir_path.mkdir()
        with patch("shutil.rmtree") as mock_rmtree:
            clean_output(dir_path, dry_run=True, no_clean=False)
            mock_rmtree.assert_not_called()
            assert dir_path.exists()

    def test_removes_existing_dir(self, tmp_path: Path):
        dir_path = tmp_path / "subdir"
        dir_path.mkdir()
        clean_output(dir_path, dry_run=False, no_clean=False)
        assert not dir_path.exists()


# ---------------------------------------------------------------------------
# generate_commons
# ---------------------------------------------------------------------------


class TestGenerateCommons:
    @patch("allotrope_gen.pipeline.run", return_value=True)
    @patch("allotrope_gen.pipeline.merged_commons_yaml")
    @patch("allotrope_gen.pipeline.patch_java_pom")
    def test_generate_commons_success(
        self, mock_patch: MagicMock, mock_merge: MagicMock, mock_run: MagicMock, tmp_path: Path
    ):
        mock_merge.return_value = tmp_path / "commons-merged.yaml"
        
        with patch("allotrope_gen.pipeline.OUTPUT", tmp_path):
            ok = generate_commons(["java", "python"], dry_run=False, no_clean=False)
            
            assert ok is True
            assert mock_run.call_count == 2
            mock_patch.assert_called_once()  # Called only for Java
            
    @patch("allotrope_gen.pipeline.run", side_effect=[True, False])
    @patch("allotrope_gen.pipeline.merged_commons_yaml")
    @patch("allotrope_gen.pipeline.patch_java_pom")
    def test_generate_commons_failure(
        self, mock_patch: MagicMock, mock_merge: MagicMock, mock_run: MagicMock, tmp_path: Path
    ):
        mock_merge.return_value = tmp_path / "commons-merged.yaml"
        
        with patch("allotrope_gen.pipeline.OUTPUT", tmp_path):
            ok = generate_commons(["java", "python"], dry_run=False, no_clean=False)
            
            assert ok is False


# ---------------------------------------------------------------------------
# generate_specs
# ---------------------------------------------------------------------------


class TestGenerateSpecs:
    @patch("allotrope_gen.pipeline.run", return_value=True)
    @patch("allotrope_gen.pipeline.schemas_referenced_from_commons", return_value={"Foo"})
    @patch("allotrope_gen.pipeline.patch_java_pom")
    def test_generate_specs_success(
        self, mock_patch: MagicMock, mock_refs: MagicMock, mock_run: MagicMock, tmp_path: Path
    ):
        dummy_spec = tmp_path / "gc.yaml"
        dummy_spec.write_text("openapi: 3.1.0", encoding="utf-8")
        
        with patch("allotrope_gen.pipeline.SPECS", {"gc": dummy_spec}), \
             patch("allotrope_gen.pipeline.OUTPUT", tmp_path):
            
            ok = generate_specs(["gc"], ["java", "python"], dry_run=False, no_clean=False)
            
            assert ok is True
            assert mock_run.call_count == 2
            mock_patch.assert_called_once()  # Called only for Java

    @patch("allotrope_gen.pipeline.run", return_value=True)
    def test_missing_spec_file_fails(self, mock_run: MagicMock, tmp_path: Path):
        nonexistent = tmp_path / "nonexistent.yaml"
        
        with patch("allotrope_gen.pipeline.SPECS", {"gc": nonexistent}):
            ok = generate_specs(["gc"], ["java"], dry_run=False, no_clean=False)
            
            assert ok is False
            mock_run.assert_not_called()
