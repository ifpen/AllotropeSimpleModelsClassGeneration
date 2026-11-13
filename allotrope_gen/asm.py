"""Locate a local checkout of the authoritative Allotrope ASM repository.

ASM JSON Schemas, examples, and manifests are licensed source material and
must not be copied into this project. Developers and sandbox agents work from
the complete upstream repository checkout instead.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent.parent
ASM_REPOSITORY_URL = "https://gitlab.com/allotrope-public/asm.git"
ASM_SCHEMA_ROOT = Path("json-schemas/adm")
LC_EMBEDDED_SCHEMA_NAME = "liquid-chromatography.tabular.embed.schema.json"
REC_VERSION_PATTERN = re.compile(r"REC/(\d{4})/(\d{2})")


def asm_repository_candidates() -> tuple[Path, ...]:
    """Return configured and project-local locations for an ASM checkout.

    ``ASM_REPO`` from the process environment takes precedence over the local
    ``.env`` value, which takes precedence over the ignored project-local
    ``target/asm`` clone. Relative paths are resolved from the project root.
    """
    candidates: list[Path] = []
    configured = os.environ.get("ASM_REPO")
    if not configured:
        configured = dotenv_values(ROOT / ".env").get("ASM_REPO")
    if configured:
        configured_path = Path(configured).expanduser()
        if not configured_path.is_absolute():
            configured_path = ROOT / configured_path
        candidates.append(configured_path)

    candidates.append(ROOT / "target" / "asm")

    # Preserve order while avoiding duplicate paths (for example, if the
    # environment variable already points at target/asm).
    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = os.path.normcase(str(candidate.resolve(strict=False)))
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return tuple(unique)


def find_asm_repository() -> Path | None:
    """Return the first valid local ASM checkout, if one is available."""
    for candidate in asm_repository_candidates():
        if (candidate / "json-schemas").is_dir() and (candidate / "test").is_dir():
            return candidate.resolve()
    return None


def require_asm_repository() -> Path:
    """Return the ASM checkout or raise an actionable setup error."""
    repository = find_asm_repository()
    if repository is None:
        candidates = "\n".join(f"  - {path}" for path in asm_repository_candidates())
        raise FileNotFoundError(
            "The complete Allotrope ASM repository is required for this operation. "
            f"Copy .env.example to .env and clone {ASM_REPOSITORY_URL} to "
            "target/asm, or configure ASM_REPO in .env. "
            "Checked locations:\n"
            f"{candidates}"
        )
    return repository


def latest_lc_schema(repository: Path | None = None) -> Path | None:
    """Find the newest released LC embedded schema in an ASM checkout.

    Candidate releases are ordered by the year and month in their ``REC`` path,
    so a newly pulled ASM release is used automatically without copying or
    pinning that schema in this repository.
    """
    repository = repository or find_asm_repository()
    if repository is None:
        return None

    schema_root = repository / ASM_SCHEMA_ROOT / "liquid-chromatography"
    candidates: list[tuple[tuple[int, int], Path]] = []
    if not schema_root.is_dir():
        return None

    for schema_path in schema_root.rglob(LC_EMBEDDED_SCHEMA_NAME):
        match = REC_VERSION_PATTERN.search(schema_path.as_posix())
        if match:
            version = (int(match.group(1)), int(match.group(2)))
            candidates.append((version, schema_path))

    if not candidates:
        return None
    return max(candidates, key=lambda candidate: candidate[0])[1]
