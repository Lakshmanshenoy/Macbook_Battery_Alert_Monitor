#!/usr/bin/env python3
"""Prepare release files: update pyproject.toml and src/battery_alert/constants.py

Usage: python3 scripts/semantic_prepare.py 1.2.3
"""
import sys
from pathlib import Path
import re


def update_pyproject(version: str) -> None:
    p = Path('pyproject.toml')
    txt = p.read_text()
    txt_new = re.sub(r'(?m)^version\s*=\s*"[^"]+"', f'version = "{version}"', txt)
    p.write_text(txt_new)


def update_constants(version: str) -> None:
    p = Path('src/battery_alert/constants.py')
    txt = p.read_text()
    txt_new = re.sub(r'APP_VERSION\s*=\s*"[^"]+"', f'APP_VERSION = "{version}"', txt)
    p.write_text(txt_new)


def main():
    if len(sys.argv) < 2:
        print('Usage: semantic_prepare.py <version>')
        sys.exit(2)
    version = sys.argv[1]
    print(f'Preparing files for version {version}')
    update_pyproject(version)
    update_constants(version)
    print('Prepared version files')


if __name__ == '__main__':
    main()
