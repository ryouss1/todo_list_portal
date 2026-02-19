"""Convert .po files to JSON for JavaScript i18n."""

import json
import os
import sys

import polib

# Project root
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def convert_po_to_json(po_path: str, json_path: str):
    """Convert a .po file to a JSON dictionary for JS consumption."""
    po = polib.pofile(po_path)
    messages = {}
    for entry in po:
        if entry.msgstr and not entry.obsolete:
            messages[entry.msgid] = entry.msgstr
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2, sort_keys=True)


def main():
    locales = sys.argv[1:] if len(sys.argv) > 1 else ["ja", "en"]
    for locale in locales:
        po_path = os.path.join(ROOT, "translations", locale, "LC_MESSAGES", "messages.po")
        json_path = os.path.join(ROOT, "static", "locale", f"{locale}.json")
        if os.path.exists(po_path):
            convert_po_to_json(po_path, json_path)
            print(f"Generated {json_path}")
        else:
            print(f"Skipped {locale}: {po_path} not found")


if __name__ == "__main__":
    main()
