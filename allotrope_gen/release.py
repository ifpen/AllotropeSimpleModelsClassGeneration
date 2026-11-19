"""
Publishing plan of a workflow run: what to generate, and whether to publish.

The ``prepare`` job of ``.github/workflows/generate.yml`` runs this module
(``python -m allotrope_gen.release``) to turn the triggering event into job
outputs.  The rules (see ``PUBLISHING.md``):

* **GitHub release published** — publishes every module.  The tag
  (``v2026.09.0`` or ``v2026.09.0-beta.2``) must equal ``COMMONS_VERSION`` and
  every spec's ``info.version``; a pre-release label in the tag publishes that
  pre-release and requires the GitHub release to be marked as pre-release (and
  vice versa).
* **Manual run** (``workflow_dispatch``) — publishes only a pre-release
  (``prerelease`` input).  Without a label, or with ``dry_run``, nothing is
  published: final versions are only published from a GitHub release.
* **Push** — generates and builds (verification only), never publishes.
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field

from .command import module_version
from .config import COMMONS_VERSION, LANGUAGES, PRERELEASE_PATTERN, SPECS

#: Release tag: ``v`` + Maven-form version, optionally ``-<label>``.
TAG_PATTERN = re.compile(r"v?(?P<version>\d{4}\.\d{2}\.\d+)(?:-(?P<label>[a-z]+\.\d+))?")


@dataclass
class Plan:
    """Outcome of :func:`plan` for one workflow run.

    Attributes:
        specs:      Instrument specs to generate.
        langs:      Languages to generate.
        publish:    Whether the publish jobs run.
        dry_run:    Whether generation only prints the generator commands.
        prerelease: Pre-release label (``beta.1``) or ``None`` for a release.
        errors:     Reasons the run must stop before generating anything.
        notices:    Informational messages for the run log.
    """

    specs: list[str]
    langs: list[str]
    publish: bool = False
    dry_run: bool = False
    prerelease: str | None = None
    errors: list[str] = field(default_factory=list)
    notices: list[str] = field(default_factory=list)


def module_versions() -> dict[str, str]:
    """Return the version (Maven form) of the commons module and every spec."""
    return {"commons": COMMONS_VERSION, **{spec: module_version(spec) for spec in SPECS}}


def plan(
    event: str,
    *,
    specs: str = "",
    langs: str = "",
    dry_run: bool = False,
    prerelease: str = "",
    tag: str = "",
    github_prerelease: bool = False,
    versions: dict[str, str] | None = None,
) -> Plan:
    """Decide what a run of the generation workflow does.

    Args:
        event:             ``github.event_name`` (``release``, ``workflow_dispatch``, ``push``).
        specs:             Space-separated ``specs`` input (manual runs; empty = all).
        langs:             Space-separated ``langs`` input (manual runs; empty = all).
        dry_run:           ``dry_run`` input (manual runs).
        prerelease:        ``prerelease`` input (manual runs).
        tag:               Release tag name (release events).
        github_prerelease: Whether the GitHub release is marked as pre-release.
        versions:          Module versions (defaults to :func:`module_versions`).

    Returns:
        The :class:`Plan`; a non-empty ``errors`` list means the run must fail.
    """
    if event != "workflow_dispatch":
        specs = langs = prerelease = ""
        dry_run = False
    result = Plan(specs=specs.split() or list(SPECS), langs=langs.split() or list(LANGUAGES))
    unknown_specs = sorted(set(result.specs) - set(SPECS))
    unknown_langs = sorted(set(result.langs) - set(LANGUAGES))
    if unknown_specs or unknown_langs:
        result.errors.append(f"Unknown specs {unknown_specs} or languages {unknown_langs}")

    if event == "release":
        match = TAG_PATTERN.fullmatch(tag)
        if match is None:
            result.errors.append(
                f"Release tag {tag!r} must look like v2026.09.0 or v2026.09.0-beta.1"
            )
            return result
        label = match["label"]
        if label is not None and not PRERELEASE_PATTERN.fullmatch(label):
            result.errors.append(f"Pre-release label {label!r} in tag {tag!r}: use alpha.N, beta.N or rc.N")
        if bool(label) != github_prerelease:
            result.errors.append(
                f"Tag {tag!r} {'has' if label else 'has no'} pre-release label but the GitHub "
                f"release is {'not ' if not github_prerelease else ''}marked as pre-release"
            )
        mismatched = {
            module: version
            for module, version in (versions or module_versions()).items()
            if version != match["version"]
        }
        if mismatched:
            result.errors.append(
                f"Tag version {match['version']} differs from module versions {mismatched}; "
                "update COMMONS_VERSION / info.version or the tag"
            )
        result.publish = True
        result.prerelease = label
    elif event == "workflow_dispatch":
        result.dry_run = dry_run
        if prerelease and not PRERELEASE_PATTERN.fullmatch(prerelease):
            result.errors.append(f"Invalid pre-release {prerelease!r}: use alpha.N, beta.N or rc.N")
        result.prerelease = prerelease or None
        result.publish = bool(prerelease) and not dry_run
        if not prerelease and not dry_run:
            result.notices.append(
                "No pre-release label: generating and building only. Final versions are "
                "published by publishing a GitHub release whose tag matches the versions."
            )
    else:
        result.notices.append(f"{event} event: generating and building only, nothing is published.")
    return result


def github_outputs(result: Plan) -> dict[str, str]:
    """Return the ``prepare`` job outputs for *result*."""
    return {
        "modules": json.dumps({"include": [{"module": m} for m in ["commons", *result.specs]]}),
        "specs": json.dumps({"include": [{"spec": s} for s in result.specs]}),
        "langs": json.dumps(result.langs),
        "spec_list": " ".join(result.specs),
        "lang_list": " ".join(result.langs),
        "dry_run": str(result.dry_run).lower(),
        "publish": str(result.publish).lower(),
        "prerelease": result.prerelease or "",
    }


def main() -> int:
    """Read the event from the environment and write ``$GITHUB_OUTPUT``."""
    env = os.environ
    result = plan(
        env.get("EVENT_NAME", ""),
        specs=env.get("REQUESTED_SPECS", ""),
        langs=env.get("REQUESTED_LANGS", ""),
        dry_run=env.get("DRY_RUN", "") == "true",
        prerelease=env.get("PRERELEASE", ""),
        tag=env.get("RELEASE_TAG", ""),
        github_prerelease=env.get("RELEASE_PRERELEASE", "") == "true",
    )
    for notice in result.notices:
        print(f"::notice::{notice}")
    for error in result.errors:
        print(f"::error::{error}")
    if result.errors:
        return 1
    outputs = github_outputs(result)
    print(json.dumps(outputs, indent=2))
    target = env.get("GITHUB_OUTPUT")
    if target:
        with open(target, "a", encoding="utf-8") as stream:
            for key, value in outputs.items():
                stream.write(f"{key}={value}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
