"""Tests for :mod:`allotrope_gen.release` (publishing plan of a workflow run)."""

from __future__ import annotations

import json

import pytest

from allotrope_gen.config import LANGUAGES, SPECS
from allotrope_gen.release import github_outputs, main, module_versions, plan

VERSIONS = {"commons": "2026.09.0", "gc": "2026.09.0", "dsc": "2026.09.0", "hplc": "2026.09.0"}


class TestRelease:
    def test_final_release(self):
        result = plan("release", tag="v2026.09.0", versions=VERSIONS)
        assert not result.errors
        assert result.publish and result.prerelease is None and not result.dry_run
        assert result.specs == list(SPECS) and result.langs == list(LANGUAGES)

    def test_tag_without_v_prefix(self):
        assert not plan("release", tag="2026.09.0", versions=VERSIONS).errors

    def test_prerelease_release(self):
        result = plan("release", tag="v2026.09.0-beta.2", github_prerelease=True, versions=VERSIONS)
        assert not result.errors
        assert result.publish and result.prerelease == "beta.2"

    def test_version_mismatch_is_an_error(self):
        versions = {**VERSIONS, "gc": "2026.09.1"}
        result = plan("release", tag="v2026.09.0", versions=versions)
        assert any("gc" in error for error in result.errors)

    @pytest.mark.parametrize("tag", ["release-1", "v2026.9.0", "v2026.09", "latest"])
    def test_malformed_tag(self, tag: str):
        assert plan("release", tag=tag, versions=VERSIONS).errors

    def test_invalid_label(self):
        assert plan("release", tag="v2026.09.0-preview.1", github_prerelease=True, versions=VERSIONS).errors

    @pytest.mark.parametrize("tag, flag", [("v2026.09.0", True), ("v2026.09.0-rc.1", False)])
    def test_github_prerelease_flag_must_match_label(self, tag: str, flag: bool):
        assert plan("release", tag=tag, github_prerelease=flag, versions=VERSIONS).errors

    def test_release_ignores_manual_inputs(self):
        result = plan("release", tag="v2026.09.0", specs="gc", dry_run=True, versions=VERSIONS)
        assert result.specs == list(SPECS) and not result.dry_run


class TestManualRun:
    def test_prerelease_publishes(self):
        result = plan("workflow_dispatch", prerelease="beta.3")
        assert result.publish and result.prerelease == "beta.3" and not result.errors

    def test_without_label_never_publishes(self):
        result = plan("workflow_dispatch")
        assert not result.publish and not result.errors and result.notices

    def test_dry_run_never_publishes(self):
        result = plan("workflow_dispatch", prerelease="beta.3", dry_run=True)
        assert not result.publish and result.dry_run

    def test_subsets(self):
        result = plan("workflow_dispatch", specs="gc", langs="java python", prerelease="beta.1")
        assert result.specs == ["gc"] and result.langs == ["java", "python"]

    def test_unknown_spec(self):
        assert plan("workflow_dispatch", specs="typo").errors

    def test_invalid_label(self):
        assert plan("workflow_dispatch", prerelease="beta").errors


def test_push_only_builds():
    result = plan("push")
    assert not result.publish and not result.dry_run and result.prerelease is None


def test_real_module_versions_cover_every_module():
    versions = module_versions()
    assert set(versions) == {"commons", *SPECS}


def test_outputs_and_main(tmp_path, monkeypatch, capsys):
    output = tmp_path / "out"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    monkeypatch.setenv("EVENT_NAME", "workflow_dispatch")
    monkeypatch.setenv("REQUESTED_SPECS", "gc dsc")
    monkeypatch.setenv("PRERELEASE", "beta.1")
    assert main() == 0
    lines = dict(line.split("=", 1) for line in output.read_text(encoding="utf-8").splitlines())
    assert lines["publish"] == "true" and lines["prerelease"] == "beta.1"
    assert lines["spec_list"] == "gc dsc"
    assert json.loads(lines["modules"]) == {"include": [{"module": m} for m in ["commons", "gc", "dsc"]]}
    assert github_outputs(plan("push"))["publish"] == "false"


def test_main_reports_errors(monkeypatch, capsys):
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    monkeypatch.setenv("EVENT_NAME", "release")
    monkeypatch.setenv("RELEASE_TAG", "not-a-version")
    assert main() == 1
    assert "::error::" in capsys.readouterr().out
