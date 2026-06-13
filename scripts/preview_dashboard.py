from __future__ import annotations

import argparse
import re
import sys
import webbrowser
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Optional local smoke check for a generated static dashboard.")
    parser.add_argument("dashboard_file", type=Path)
    parser.add_argument("--open", action="store_true", help="Attempt to open the local file in the system browser.")
    args = parser.parse_args(argv)
    try:
        text = args.dashboard_file.read_text(encoding="utf-8")
    except Exception as error:
        print(f"warning: failed to read dashboard: {error}")
        return 0
    title = re.search(r"<title>(.*?)</title>", text, re.IGNORECASE | re.DOTALL)
    section_count = len(re.findall(r'<section class="section">', text))
    print(f"title: {title.group(1) if title else 'missing'}")
    print(f"section_count: {section_count}")
    if any(token in text.lower() for token in ("<script", "http://", "https://", "<link")):
        print("warning: external or scripted content marker detected")
    if args.open:
        try:
            opened = webbrowser.open(args.dashboard_file.resolve().as_uri())
            if not opened:
                print("warning: browser open was unavailable")
        except Exception as error:
            print(f"warning: browser open failed: {error}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
