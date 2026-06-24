"""
OpenAPI generator command builders.

Responsible for constructing the ``openapi-generator-cli`` argument lists that
are passed to :func:`~allotrope_gen.pipeline.run`.

**Design note — config file over CLI flags**
    All generator properties are written to a JSON config file
    (``openapi-generator-config.json``) rather than being passed as individual
    ``--additional-properties`` flags.  This avoids shell-quoting problems on
    Windows where ``subprocess.run`` with ``shell=True`` is required for ``.cmd``
    wrappers, and it keeps the argument list short and readable in ``--dry-run``
    output.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .config import LanguageConfig


def to_pascal(s: str) -> str:
    """Return *s* capitalised (``"gc"`` → ``"Gc"``).

    Re-exported here for convenience; the canonical definition lives in
    :mod:`allotrope_gen.config`.
    """
    from .config import to_pascal as _tp
    return _tp(s)


def generator_cli() -> str:
    """Return the platform-appropriate ``openapi-generator-cli`` executable name.

    On Windows, npm installs a ``.cmd`` wrapper that ``subprocess`` cannot find
    when ``shell=False``.  Callers in :mod:`~allotrope_gen.pipeline` pass
    ``shell=True`` on Windows to work around this, but the executable name must
    still include the ``.cmd`` suffix for the PATH lookup to succeed.
    """
    return "openapi-generator-cli.cmd" if sys.platform == "win32" else "openapi-generator-cli"


def interpolate(value: str, spec: str) -> str:
    """Expand ``{spec}``-family placeholders in *value*.

    Supported placeholders:

    ``{spec}``
        The raw spec key (e.g. ``"gc"``).
    ``{spec_pascal}``
        PascalCase version (e.g. ``"Gc"``).
    ``{spec_upper}``
        Upper-case version (e.g. ``"GC"``).

    Examples::

        >>> interpolate("allotrope-models-{spec}", "gc")
        'allotrope-models-gc'
        >>> interpolate("Models{spec_pascal}", "gc")
        'ModelsGc'
        >>> interpolate("no placeholders", "gc")
        'no placeholders'
    """
    from .config import to_pascal as _tp
    return (
        value
        .replace("{spec}", spec)
        .replace("{spec_pascal}", _tp(spec))
        .replace("{spec_upper}", spec.upper())
    )


def write_config(
    props: dict[str, str],
    spec: str,
    cfg: LanguageConfig,
    output_dir: Path,
) -> Path:
    """Write the generator config JSON to *output_dir* and return its path.

    The config file is preferred over CLI ``--additional-properties`` flags to
    avoid shell-quoting issues on Windows.  The language-specific package key
    (e.g. ``modelPackage``, ``packageName``) is injected here because
    ``--config`` takes precedence over other CLI flags when both are present.

    Args:
        props:      Raw ``extra_props`` from :class:`~allotrope_gen.config.LanguageConfig`,
                    whose values may contain ``{spec}`` placeholders.
        spec:       Current spec identifier (``""`` for the commons library).
        cfg:        Language configuration.
        output_dir: Directory where the config file will be written.

    Returns:
        Path to the written ``openapi-generator-config.json``.
    """
    resolved = {k: interpolate(v, spec) for k, v in props.items()}
    resolved[cfg.package_key] = cfg.package_fn(spec)
    config_path = output_dir / "openapi-generator-config.json"
    config_path.write_text(
        json.dumps(resolved, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return config_path


def build_import_mappings(common_schemas: set[str], cfg: LanguageConfig) -> str:
    """Build the comma-separated ``--import-mappings`` value.

    Args:
        common_schemas: Schema names from the commons library that this spec
                        references and should therefore *not* be re-generated.
        cfg:            Language configuration that provides the import pattern
                        and commons package identifier.

    Returns:
        A comma-separated string of ``ClassName=package`` pairs, or ``""`` when
        *common_schemas* is empty (meaning ``--import-mappings`` should be
        omitted entirely).
    """
    return ",".join(
        cfg.import_pattern.format(
            class_name=name,
            commons_package=cfg.commons_package,
        )
        for name in sorted(common_schemas)
    )


def build_cmd(
    spec: str,
    spec_path: Path,
    cfg: LanguageConfig,
    common_schemas: set[str],
    output_dir: Path,
) -> list[str]:
    """Build the ``openapi-generator-cli generate`` command for an instrument spec.

    Args:
        spec:           Spec identifier (e.g. ``"gc"``).
        spec_path:      Path to the instrument YAML file.
        cfg:            Language configuration.
        common_schemas: Commons schemas referenced by this spec; used to build
                        ``--import-mappings``.
        output_dir:     Where the generator should write its output.

    Returns:
        Argument list suitable for :func:`subprocess.run`.
    """
    config_path = write_config(cfg.extra_props, spec, cfg, output_dir)
    import_mappings = build_import_mappings(common_schemas, cfg)

    cmd = [
        generator_cli(), "generate",
        "--input-spec",     str(spec_path),
        "--generator-name", cfg.generator,
        "--output",         str(output_dir),
        "--config",         str(config_path),
    ]
    if import_mappings:
        cmd += ["--import-mappings", import_mappings]
    cmd += cfg.extra_opts
    return cmd


def build_commons_cmd(
    merged_path: Path,
    cfg: LanguageConfig,
    output_dir: Path,
) -> list[str]:
    """Build the ``openapi-generator-cli generate`` command for the commons library.

    Uses ``spec=""`` so that :func:`write_config` and :attr:`~allotrope_gen.config.LanguageConfig.package_fn`
    produce the commons package / namespace rather than a spec-specific one.

    Args:
        merged_path: Path to the ``commons-merged.yaml`` produced by
                     :func:`~allotrope_gen.schema.merged_commons_yaml`.
        cfg:         Language configuration.
        output_dir:  Where the generator should write its output.

    Returns:
        Argument list suitable for :func:`subprocess.run`.
    """
    config_path = write_config(cfg.extra_props, "", cfg, output_dir)
    return [
        generator_cli(), "generate",
        "--input-spec",     str(merged_path),
        "--generator-name", cfg.generator,
        "--output",         str(output_dir),
        "--config",         str(config_path),
        *cfg.extra_opts,
    ]
