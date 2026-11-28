#!/usr/bin/env python3

from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET
import hashlib

ROOT = Path(__file__).resolve().parent.parent
addons = {}

def version_key(version):
    import re
    return tuple(
        (0, int(part)) if part.isdigit() else (1, part)
        for part in re.findall(r"\d+|[^\d]+", version)
    )

for folder in sorted(ROOT.glob("skin.*")):
    if not folder.is_dir():
        continue

    for package in sorted(folder.glob("*.zip")):
        with ZipFile(package) as archive:
            manifest = f"{folder.name}/addon.xml"

            if manifest not in archive.namelist():
                continue

            addon = ET.fromstring(archive.read(manifest))
            addon_id = addon.attrib["id"]
            version = addon.attrib["version"]

            if folder.name != addon_id:
                continue

            if package.name != f"{addon_id}-{version}.zip":
                continue

            previous = addons.get(addon_id)

            if previous is None or version_key(version) > version_key(
                previous.attrib["version"]
            ):
                addons[addon_id] = addon

if not addons:
    raise SystemExit("No valid skin packages found.")

root = ET.Element("addons")

for addon_id, addon in sorted(addons.items()):
    root.append(addon)
    print(f"Indexed {addon_id} v{addon.attrib['version']}")

ET.indent(root, space="    ")

xml_data = ET.tostring(
    root,
    encoding="utf-8",
    xml_declaration=True
)

(ROOT / "addons.xml").write_bytes(xml_data)

(ROOT / "addons.xml.md5").write_text(
    hashlib.md5(xml_data).hexdigest(),
    encoding="utf-8"
)

print("Repository index updated.")
