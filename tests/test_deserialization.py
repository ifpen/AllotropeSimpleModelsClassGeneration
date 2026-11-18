"""Integration tests for deserializing upstream ASM samples in all clients."""

from __future__ import annotations

import pytest

from allotrope_gen.asm import find_asm_repository
from allotrope_gen.config import LANGUAGES, SPECS
from verify_deserialization import verify_pair


@pytest.mark.parametrize("spec", list(SPECS))
@pytest.mark.parametrize("lang", list(LANGUAGES))
def test_generated_client_deserializes_asm_example(spec: str, lang: str) -> None:
    """Deserialize the latest upstream example and inspect nested content."""
    repository = find_asm_repository()
    assert repository is not None, (
        "The full ASM source checkout is required. Clone it to target/asm or "
        "set ASM_REPO (see AGENTS.md)."
    )

    assert verify_pair(spec, lang, repository), f"Deserialization failed for {spec} / {lang}"
