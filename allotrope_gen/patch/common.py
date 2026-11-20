"""
Helpers shared by every post-generation patch.

Patches edit code that openapi-generator wrote, so they must notice when a
generator upgrade changes that code.  The rules every patch follows are
implemented here:

* **fail loudly** — :func:`replace_exact` raises :class:`PatchError` when a
  pattern does not match the expected number of times, instead of silently
  leaving the generated code unpatched;
* **dry run** — :func:`write_text` only writes when ``dry_run`` is ``False``,
  so ``generate.py --dry-run`` reports what would change;
* **templates, not inline strings** — source files that patches add to the
  generated code live in ``allotrope_gen/patch/templates`` as real ``.cs`` /
  ``.py`` files and are rendered by :func:`render_template`.
"""

from __future__ import annotations

import re
from pathlib import Path
from string import Template

#: Directory holding the source files that patches add to generated code.
TEMPLATES = Path(__file__).parent / "templates"


class PatchError(RuntimeError):
    """Raised when generated code no longer has the shape a patch expects.

    The pipeline reports it and fails the run: a generator upgrade that
    changes the patched code must be looked at, not ignored.
    """


def replace_exact(text: str, pattern: str, replacement: str, path: Path, expected: int = 1) -> str:
    """Apply a multi-line regex substitution that must match *expected* times.

    Args:
        text:        Source text.
        pattern:     Regular expression (``re.MULTILINE``).
        replacement: Replacement, as for :func:`re.subn`.
        path:        File the text comes from (for the error message).
        expected:    Exact number of matches required.

    Returns:
        The substituted text.

    Raises:
        PatchError: If the number of matches differs from *expected*.
    """
    patched, count = re.subn(pattern, replacement, text, flags=re.MULTILINE)
    if count != expected:
        raise PatchError(f"{path}: expected {expected} match(es) of {pattern!r}, found {count}")
    return patched


def write_text(path: Path, text: str, dry_run: bool) -> None:
    """Write *text* to *path* as UTF-8, unless *dry_run*."""
    if not dry_run:
        path.write_text(text, encoding="utf-8")


def render_template(name: str, **values: str) -> str:
    """Render ``templates/<name>`` with :class:`string.Template` placeholders.

    Templates use ``${placeholder}``; a literal ``$`` must be written ``$$``.
    The C# templates therefore avoid interpolated strings (``$"…"``).

    Raises:
        KeyError: If the template uses a placeholder missing from *values*.
    """
    return Template((TEMPLATES / name).read_text(encoding="utf-8")).substitute(values)


def report(tag: str, message: str) -> None:
    """Print a patch progress line (``  [tag] message``)."""
    print(f"  [{tag}] {message}")


def snake_case(name: str) -> str:
    """Return the generators' snake_case form of a PascalCase class name."""
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def lower_camel(name: str) -> str:
    """Return *name* with a lower-case first letter (generated variable names)."""
    return name[:1].lower() + name[1:]


def attribute_name(json_property: str) -> str:
    """Return the identifier generators derive from a JSON property name."""
    return re.sub(r"\W+", "_", json_property).strip("_").lower()
