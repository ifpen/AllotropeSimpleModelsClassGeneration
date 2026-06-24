#!/usr/bin/env python3
"""
Verify generated builds locally using containerized SDKs (Docker/Podman).

This script mounts the workspace into official Docker images to compile
and build the generated code, matching the CI/CD environment without
requiring SDK installations on the host system.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Add project root to python path to import config
ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT))

from allotrope_gen.config import LANGUAGES, SPECS, OUTPUT


def check_docker() -> bool:
    """Return True if Docker is installed and running."""
    try:
        subprocess.run(
            ["docker", "info"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def get_docker_cmd(
    image: str,
    workdir_rel: str,
    run_cmd: str,
) -> list[str]:
    """Build the docker run command list."""
    # Convert absolute host path to format suited for docker mount
    host_workspace = str(ROOT)
    container_workspace = "/workspace"
    container_workdir = f"{container_workspace}/{workdir_rel}".replace("\\", "/")

    return [
        "docker", "run", "--rm",
        "-v", f"{host_workspace}:{container_workspace}",
        "-w", container_workdir,
        image,
        *run_cmd.split()
    ]


def verify_module_lang(
    module: str,
    lang: str,
    dry_run: bool = False,
) -> bool:
    """Run verification container for a given module and language."""
    cfg = LANGUAGES[lang]
    # Locate generated output directory relative to project root
    out_rel = OUTPUT.relative_to(ROOT) / module / cfg.output_subdir
    out_path = ROOT / out_rel

    if not out_path.exists():
        print(f"Skipping verification for {module} ({lang}): output dir does not exist.")
        return True

    # Setup container configuration based on language
    if lang == "java":
        image = "maven:3.9-eclipse-temurin-17"
        run_cmd = "mvn clean compile"
    elif lang == "csharp":
        image = "mcr.microsoft.com/dotnet/sdk:8.0"
        run_cmd = "dotnet build --configuration Release"
    elif lang == "python":
        image = "python:3.12"
        # Run pip install build and python -m build via bash -c
        image_cmd = ["bash", "-c", "pip install build && python -m build"]
        host_workspace = str(ROOT)
        container_workspace = "/workspace"
        container_workdir = f"{container_workspace}/{out_rel}".replace("\\", "/")
        docker_cmd = [
            "docker", "run", "--rm",
            "-v", f"{host_workspace}:{container_workspace}",
            "-w", container_workdir,
            image,
            *image_cmd
        ]
        
        print(f"\n--- Verifying {module} ({lang}) in {image} ---")
        print(f"Command: {' '.join(docker_cmd)}")
        if dry_run:
            return True
        res = subprocess.run(docker_cmd)
        return res.returncode == 0
    elif lang == "typescript-angular":
        image = "node:20"
        run_cmd = "npm install"
    else:
        print(f"No container verification setup for language: {lang}")
        return True

    docker_cmd = get_docker_cmd(image, str(out_rel), run_cmd)
    
    print(f"\n--- Verifying {module} ({lang}) in {image} ---")
    print(f"Command: {' '.join(docker_cmd)}")
    if dry_run:
        return True

    res = subprocess.run(docker_cmd)
    return res.returncode == 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--specs", nargs="+", default=["commons"] + list(SPECS),
        help="Modules to verify (commons, gc, etc.). Default is all.",
    )
    parser.add_argument(
        "--langs", nargs="+", default=list(LANGUAGES),
        help="Languages to verify (java, csharp, python, typescript-angular). Default is all.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print verify commands without running them.",
    )
    args = parser.parse_args(argv)

    if not args.dry_run and not check_docker():
        print("[ERROR] Docker is not installed or not running. Start Docker/Podman to continue.", file=sys.stderr)
        return 1

    success = True
    for module in args.specs:
        for lang in args.langs:
            if lang not in LANGUAGES:
                print(f"[ERROR] Unknown language: {lang}", file=sys.stderr)
                return 1
            if module != "commons" and module not in SPECS:
                print(f"[ERROR] Unknown spec: {module}", file=sys.stderr)
                return 1
                
            ok = verify_module_lang(module, lang, dry_run=args.dry_run)
            if not ok:
                print(f"[FAIL] Build failed for module: {module}, language: {lang}", file=sys.stderr)
                success = False

    if success:
        print("\n[SUCCESS] All checked builds completed successfully!")
        return 0
    else:
        print("\n[FAILURE] Some builds failed to compile.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
