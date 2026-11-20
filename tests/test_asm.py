"""Tests for locating the separate authoritative ASM checkout."""

from __future__ import annotations

from pathlib import Path

from allotrope_gen import asm


def test_configured_asm_repository_is_preferred_and_validated(
    tmp_path: Path, monkeypatch
) -> None:
    """Honor ASM_REPO when it points at a complete source checkout."""
    repository = tmp_path / "authoritative-asm"
    (repository / "json-schemas").mkdir(parents=True)
    (repository / "test").mkdir()
    monkeypatch.setenv("ASM_REPO", str(repository))

    assert asm.find_asm_repository() == repository.resolve()
    assert asm.asm_repository_candidates()[0] == repository


def test_dotenv_path_is_project_relative_and_process_environment_wins(
    tmp_path: Path, monkeypatch
) -> None:
    """Read local .env paths relative to root, with shell override support."""
    root = tmp_path / "project"
    root.mkdir()
    dotenv_repository = root / "external-asm"
    environment_repository = root / "environment-asm"
    monkeypatch.setattr(asm, "ROOT", root)
    monkeypatch.delenv("ASM_REPO", raising=False)
    (root / ".env").write_text("ASM_REPO=./external-asm\n", encoding="utf-8")

    assert asm.asm_repository_candidates()[0] == dotenv_repository

    monkeypatch.setenv("ASM_REPO", str(environment_repository))
    assert asm.asm_repository_candidates()[0] == environment_repository


def test_missing_checkout_error_documents_supported_locations(
    tmp_path: Path, monkeypatch
) -> None:
    """Give developers clear setup instructions when the source clone is absent."""
    missing = tmp_path / "missing"
    monkeypatch.setattr(asm, "asm_repository_candidates", lambda: (missing,))

    try:
        asm.require_asm_repository()
    except FileNotFoundError as exc:
        message = str(exc)
    else:
        raise AssertionError("Expected a missing ASM checkout to be reported")

    assert asm.ASM_REPOSITORY_URL in message
    assert "target/asm" in message
    assert "ASM_REPO" in message


def test_latest_lc_schema_uses_newest_rec_release(tmp_path: Path) -> None:
    """Discover new official releases from the full ASM checkout automatically."""
    schema_root = tmp_path / "json-schemas/adm/liquid-chromatography"
    old = (
        schema_root
        / "REC/2026/09/liquid-chromatography.tabular.embed.schema.json"
    )
    current = (
        schema_root
        / "REC/2027/03/liquid-chromatography.tabular.embed.schema.json"
    )
    for schema in (old, current):
        schema.parent.mkdir(parents=True, exist_ok=True)
        schema.write_text("{}", encoding="utf-8")

    assert asm.latest_lc_schema(tmp_path) == current
