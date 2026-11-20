"""Tests for :mod:`allotrope_gen.pipeline`."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from allotrope_gen.patch import PatchError
from allotrope_gen.pipeline import (
    clean_output,
    commons_dependency,
    generate_commons,
    generate_specs,
    patch_targets,
    run,
)


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
    @patch("allotrope_gen.pipeline.patch_commons_output")
    def test_generate_commons_success(
        self, mock_patch: MagicMock, mock_merge: MagicMock, mock_run: MagicMock, tmp_path: Path
    ):
        mock_merge.return_value = tmp_path / "commons-merged.yaml"
        
        with patch("allotrope_gen.pipeline.OUTPUT", tmp_path):
            ok = generate_commons(["java", "python"], dry_run=False, no_clean=False)
            
            assert ok is True
            assert mock_run.call_count == 2
            assert [c.args[0] for c in mock_patch.call_args_list] == ["java", "python"]
            
    @patch("allotrope_gen.pipeline.run", side_effect=[True, False])
    @patch("allotrope_gen.pipeline.merged_commons_yaml")
    @patch("allotrope_gen.pipeline.patch_commons_output")
    def test_generate_commons_failure(
        self, mock_patch: MagicMock, mock_merge: MagicMock, mock_run: MagicMock, tmp_path: Path
    ):
        mock_merge.return_value = tmp_path / "commons-merged.yaml"
        
        with patch("allotrope_gen.pipeline.OUTPUT", tmp_path):
            ok = generate_commons(["java", "python"], dry_run=False, no_clean=False)
            
            assert ok is False
            mock_patch.assert_called_once()  # Only the successful run is patched

    @patch("allotrope_gen.pipeline.run", return_value=True)
    @patch("allotrope_gen.pipeline.merged_commons_yaml")
    @patch("allotrope_gen.pipeline.patch_commons_output", side_effect=PatchError("shape changed"))
    def test_patch_error_fails_the_run(
        self, mock_patch: MagicMock, mock_merge: MagicMock, mock_run: MagicMock,
        tmp_path: Path, capsys: pytest.CaptureFixture[str],
    ):
        mock_merge.return_value = tmp_path / "commons-merged.yaml"
        with patch("allotrope_gen.pipeline.OUTPUT", tmp_path):
            assert generate_commons(["csharp"], dry_run=False, no_clean=False) is False
        assert "[ERROR] shape changed" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# generate_specs
# ---------------------------------------------------------------------------


class TestGenerateSpecs:
    @patch("allotrope_gen.pipeline.enrich_spec_descriptions")
    @patch("allotrope_gen.pipeline.run", return_value=True)
    @patch("allotrope_gen.pipeline.patch_spec_output")
    def test_generate_specs_success(
        self,
        mock_patch: MagicMock,
        mock_run: MagicMock,
        mock_enrich: MagicMock,
        tmp_path: Path,
    ):
        dummy_spec = tmp_path / "gc.yaml"
        dummy_spec.write_text("openapi: 3.1.0", encoding="utf-8")
        bundled = tmp_path / "gc.bundled.yaml"
        bundled.write_text("components:\n  schemas: {}\n", encoding="utf-8")

        with patch("allotrope_gen.pipeline.SPECS", {"gc": dummy_spec}), \
             patch("allotrope_gen.pipeline.OUTPUT", tmp_path), \
             patch("allotrope_gen.pipeline.bundle_spec", return_value=(bundled, {"Foo"})) as mock_bundle:

            ok = generate_specs(["gc"], ["java", "python"], dry_run=False, no_clean=False)

            assert ok is True
            assert mock_run.call_count == 2
            # The generator receives the bundled spec, not the source file.
            assert all(str(bundled) in call.args[0] for call in mock_run.call_args_list)
            mock_bundle.assert_called_once()
            assert [c.args[0] for c in mock_patch.call_args_list] == ["java", "python"]
            # Both outputs depend on commons (the spec reaches a commons schema).
            assert all(c.args[4] is not None for c in mock_patch.call_args_list)
            mock_enrich.assert_called_once_with(dummy_spec)

    @patch("allotrope_gen.pipeline.run", return_value=True)
    def test_missing_spec_file_fails(self, mock_run: MagicMock, tmp_path: Path):
        nonexistent = tmp_path / "nonexistent.yaml"
        
        with patch("allotrope_gen.pipeline.SPECS", {"gc": nonexistent}):
            ok = generate_specs(["gc"], ["java"], dry_run=False, no_clean=False)
            
            assert ok is False
            mock_run.assert_not_called()


# ---------------------------------------------------------------------------
# commons_dependency / patch_targets
# ---------------------------------------------------------------------------


class TestCommonsDependency:
    @pytest.mark.parametrize("lang, name, version, group", [
        ("java", "allotrope-models-commons", "2026.09.0", "fr.ifpen.allotropeconverters"),
        ("csharp", "IFPEN.AllotropeConverters.AllotropeModels.Commons", "2026.9.0", ""),
        ("typescript-angular", "@ifpen/allotrope-models-commons", "2026.9.0", ""),
        ("python", "ifpen.allotrope_models", "2026.9.0", ""),
    ])
    def test_release(self, lang: str, name: str, version: str, group: str):
        dependency = commons_dependency(lang, {"Foo"})
        assert (dependency.name, dependency.version, dependency.maven_group) == (name, version, group)
        assert dependency.schemas == frozenset({"Foo"})

    @pytest.mark.parametrize("lang, expected", [
        ("java", "2026.09.0-beta1"),
        ("csharp", "2026.9.0-beta.1"),
        ("typescript-angular", "2026.9.0-beta.1"),
        ("python", "2026.9.0b1"),
    ])
    def test_prerelease(self, lang: str, expected: str):
        assert commons_dependency(lang, {"Foo"}, prerelease="beta.1").version == expected


class TestPatchTargets:
    SCHEMAS = {
        "Q": {"type": "object", "properties": {"value": {"type": "number", "x-asm-nan": True}}},
        "Mapped": {"type": "object", "properties": {"value": {"type": "number", "x-asm-nan": True}}},
        "U": {"oneOf": [{"type": "string"}, {"type": "object"}]},
    }

    def test_collects_targets(self):
        targets = patch_targets(self.SCHEMAS)
        assert targets.nan_properties == {"Q": ["value"], "Mapped": ["value"]}
        assert targets.primitive_unions == ["U"]

    def test_excludes_mapped_schemas(self):
        targets = patch_targets(self.SCHEMAS, exclude={"Mapped", "U"})
        assert targets.nan_properties == {"Q": ["value"]}
        assert targets.primitive_unions == []
