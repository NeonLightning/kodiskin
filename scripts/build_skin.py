#!/usr/bin/env python3
"""Build a versioned, installable Terminal 80 Kodi skin ZIP."""

import argparse
import os
from pathlib import Path
import re
import tempfile
from xml.etree import ElementTree
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


ROOT = Path(__file__).resolve().parent.parent
ADDON = ROOT / "addon.xml"
CHANGELOG = ROOT / "changelog.txt"
PACKAGE_DIRS = ("16x9", "colors", "extras", "fonts", "language", "media", "shortcuts")
PACKAGE_FILES = ("LICENSE.txt", "README.md", "addon.xml", "changelog.txt", "icon.png")
def source_files():
    missing = [name for name in PACKAGE_FILES + PACKAGE_DIRS if not (ROOT / name).exists()]
    if missing:
        raise ValueError(f"Missing package paths: {', '.join(missing)}")
    files = [ROOT / name for name in PACKAGE_FILES]
    for name in PACKAGE_DIRS:
        files.extend(path for path in (ROOT / name).rglob("*") if path.is_file())
    files = [path for path in files if not any(part.startswith(".") or part == "__pycache__" for part in path.relative_to(ROOT).parts)]
    return sorted(files, key=lambda path: path.relative_to(ROOT).as_posix())


def validate_xml(files):
    for path in files:
        if path.suffix == ".xml":
            ElementTree.parse(path)


def build(version, files):
    output = ROOT / f"skin.terminal80-{version}.zip"
    descriptor, temporary = tempfile.mkstemp(prefix=".skin-build-", suffix=".zip", dir=ROOT)
    os.close(descriptor)
    try:
        with ZipFile(temporary, "w") as archive:
            for path in files:
                relative = path.relative_to(ROOT).as_posix()
                entry = ZipInfo(f"skin.terminal80/{relative}", date_time=(1980, 1, 1, 0, 0, 0))
                entry.compress_type = ZIP_DEFLATED
                entry.external_attr = 0o644 << 16
                archive.writestr(entry, path.read_bytes(), compress_type=ZIP_DEFLATED, compresslevel=6)
        with ZipFile(temporary) as archive:
            if archive.testzip() is not None:
                raise ValueError("ZIP integrity check failed")
            if len(archive.namelist()) != len(files):
                raise ValueError("ZIP file count does not match source")
            if f'version="{version}"'.encode() not in archive.read("skin.terminal80/addon.xml"):
                raise ValueError("ZIP version does not match addon.xml")
        os.replace(temporary, output)
        os.chmod(output, 0o644)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    print(f"Built {output.name} ({len(files)} files)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bump-patch", action="store_true", help="Increment the patch version before building")
    parser.add_argument("--note", help="Changelog note required with --bump-patch")
    args = parser.parse_args()
    if args.bump_patch != bool(args.note):
        parser.error("--bump-patch and --note must be used together")
    if args.note and not args.note.strip():
        parser.error("--note must contain text")

    addon_text = ADDON.read_text()
    changelog_text = CHANGELOG.read_text()
    version = ElementTree.fromstring(addon_text).get("version")
    if not version or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
        parser.error("addon.xml must contain a numeric major.minor.patch version")
    files = source_files()
    validate_xml(files)
    if args.bump_patch:
        major, minor, patch = map(int, version.split("."))
        next_version = f"{major}.{minor}.{patch + 1}"
        if (ROOT / f"skin.terminal80-{next_version}.zip").exists():
            parser.error(f"skin.terminal80-{next_version}.zip already exists")
        updated = addon_text.replace(f'version="{version}"', f'version="{next_version}"', 1)
        if updated == addon_text:
            parser.error("could not update addon.xml version")
        ADDON.write_text(updated)
        CHANGELOG.write_text(changelog_text.rstrip() + f"\n\nTerminal 80 {next_version}\n- {args.note.strip()}\n")
        version = next_version

    try:
        build(version, files)
    except Exception:
        if args.bump_patch:
            ADDON.write_text(addon_text)
            CHANGELOG.write_text(changelog_text)
        raise


if __name__ == "__main__":
    main()
