"""SBOM generator for PlantaOS -- inventories packages, modules, JS assets."""

from __future__ import annotations

import importlib.metadata
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Project root (one level up from scripts/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _get_installed_packages() -> list[dict[str, str]]:
    """Collect all installed Python packages with versions.

    Returns:
        List of dicts with name and version keys.
    """
    packages: list[dict[str, str]] = []
    for dist in importlib.metadata.distributions():
        name = dist.metadata.get("Name", "unknown")
        version = dist.metadata.get("Version", "unknown")
        packages.append({"name": name, "version": version})
    # Sort by name for deterministic output
    packages.sort(key=lambda p: p["name"].lower())
    return packages


def _get_local_modules() -> list[str]:
    """Find all local .py modules under the project root.

    Returns:
        Sorted list of module paths relative to project root.
    """
    modules: list[str] = []
    for py_file in PROJECT_ROOT.rglob("*.py"):
        rel = py_file.relative_to(PROJECT_ROOT)
        # Skip hidden dirs, __pycache__, venv, .venv
        parts = rel.parts
        if any(
            p.startswith(".")
            or p == "__pycache__"
            or p in ("venv", ".venv", "node_modules")
            for p in parts
        ):
            continue
        modules.append(str(rel))
    modules.sort()
    return modules


def _get_js_assets() -> list[str]:
    """Find JavaScript and CSS assets in the assets/ directory.

    Returns:
        Sorted list of asset paths relative to project root.
    """
    assets_dir = PROJECT_ROOT / "assets"
    if not assets_dir.exists():
        return []
    results: list[str] = []
    for f in assets_dir.rglob("*"):
        if f.suffix in (".js", ".css", ".mjs"):
            results.append(str(f.relative_to(PROJECT_ROOT)))
    results.sort()
    return results


def _get_python_core_boundary() -> dict[str, str]:
    """Identify Python version and key runtime info.

    Returns:
        Dict with python_version, platform, and implementation.
    """
    return {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "implementation": platform.python_implementation(),
    }


def _get_git_revision() -> str | None:
    """Get the current git revision hash if available.

    Returns:
        Git short hash string or None.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    return None


def generate_sbom() -> dict:
    """Generate a full SBOM for the PlantaOS project.

    Returns:
        SBOM dict with packages, modules, assets, and metadata.
    """
    return {
        "sbom_version": "1.0",
        "project": "PlantaOS MVP",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_revision": _get_git_revision(),
        "python_core_boundary": _get_python_core_boundary(),
        "packages": _get_installed_packages(),
        "modules": _get_local_modules(),
        "js_assets": _get_js_assets(),
    }


def main() -> None:
    """Entry point: generate and print SBOM as JSON."""
    sbom = generate_sbom()
    output = json.dumps(sbom, indent=2, ensure_ascii=False)
    print(output)

    # Also write to file
    out_path = PROJECT_ROOT / "sbom.json"
    out_path.write_text(output, encoding="utf-8")
    print(f"\nSBOM written to {out_path}", file=sys.stderr)
    print(
        f"  Packages: {len(sbom['packages'])}",
        file=sys.stderr,
    )
    print(
        f"  Modules:  {len(sbom['modules'])}",
        file=sys.stderr,
    )
    print(
        f"  JS assets: {len(sbom['js_assets'])}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
