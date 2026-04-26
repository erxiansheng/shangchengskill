"""Package this Skill folder into a single distributable .zip.

Usage:
    python scripts/package_skill.py

Produces: dist/edgeone-mall-<version>.zip
"""
from __future__ import annotations
import os, re, sys, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL_MD = ROOT / "SKILL.md"


def _version() -> str:
    text = SKILL_MD.read_text(encoding="utf-8")
    m = re.search(r"^version:\s*([0-9.]+)", text, re.M)
    return m.group(1) if m else "0.0.0"


INCLUDE_DIRS = ("references", "templates", "examples", "scripts")
INCLUDE_FILES = ("SKILL.md", "PROMPT.md", "README.md", "LICENSE")
EXCLUDE_GLOBS = ("__pycache__", "node_modules", "dist", ".git", ".env", "*.pyc")


def _excluded(p: Path) -> bool:
    parts = p.parts
    for pat in EXCLUDE_GLOBS:
        if any(part == pat or (pat.startswith("*.") and part.endswith(pat[1:])) for part in parts):
            return True
    return False


def main() -> int:
    out_dir = ROOT / "dist"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / f"edgeone-mall-{_version()}.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in INCLUDE_FILES:
            p = ROOT / f
            if p.exists():
                zf.write(p, p.name)
        for d in INCLUDE_DIRS:
            base = ROOT / d
            if not base.exists():
                continue
            for path in base.rglob("*"):
                if path.is_file() and not _excluded(path.relative_to(ROOT)):
                    zf.write(path, path.relative_to(ROOT))
    print(f"wrote {out} ({out.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
