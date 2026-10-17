#!/usr/bin/env python3
"""Prepare independently downloadable Qt/PySide6 sources for a Kanyx release.

This is a reproducible archive-integrity/provenance check, NOT a proof of
complete LGPLv3 compliance or build-for-build equivalence with PyPI wheels.
Requires Python 3.11+; no third-party Python packages.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tarfile
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

QT_ROOT = 'https://download.qt.io/official_releases/qt/6.12/6.12.0/submodules/'
PYSIDE_ROOT = 'https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.12.0-src/'

# Sizes and SHA-256 digests are the published Qt MirrorBrain metadata for 6.12.0.
ARCHIVES = (
    dict(name='qtbase-everywhere-src-6.12.0.tar.xz', size=51220268,
         sha256='a951bd163c7b80fc6b8c88d7668fb56abf91c152373e13c10666763238131307',
         url=QT_ROOT + 'qtbase-everywhere-src-6.12.0.tar.xz', platforms=['Windows', 'Linux']),
    dict(name='qtsvg-everywhere-src-6.12.0.tar.xz', size=2341876,
         sha256='e4ab39534ec97987b1b9b60ef7f4d3253d5912a69f8c713a01753174a4029331',
         url=QT_ROOT + 'qtsvg-everywhere-src-6.12.0.tar.xz', platforms=['Windows', 'Linux']),
    dict(name='qtimageformats-everywhere-src-6.12.0.tar.xz', size=1848620,
         sha256='0943132b5db8de6b6a7f1d162682173e8763c7ed94e80fd39113292845f67762',
         url=QT_ROOT + 'qtimageformats-everywhere-src-6.12.0.tar.xz', platforms=['Windows', 'Linux']),
    dict(name='qtwayland-everywhere-src-6.12.0.tar.xz', size=908828,
         sha256='ae14d9bcf1bb3c300a3ab2e6a53f50284e5c6c966a4ac4cc5aedcb1bc74e4d02',
         url=QT_ROOT + 'qtwayland-everywhere-src-6.12.0.tar.xz', platforms=['Linux']),
    dict(name='pyside-setup-everywhere-src-6.12.0.tar.xz', size=18211772,
         sha256='099c1a597cf33c1b000e11cf68a0b82d216fb802bf81726efc720394f10c7751',
         url=PYSIDE_ROOT + 'pyside-setup-everywhere-src-6.12.0.tar.xz',
         platforms=['Windows', 'Linux']),
)


def download(url: str, target: Path) -> None:
    """Stream downloads to a temp file, retrying network errors safely."""
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            req = Request(url, headers={'User-Agent': 'Kanyx-source-audit/1.0'})
            with urlopen(req, timeout=120) as response, target.open('wb') as out:
                shutil.copyfileobj(response, out, length=1024 * 1024)
            return
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            last_error = exc
            target.unlink(missing_ok=True)
            if attempt < 2:
                time.sleep(2 ** attempt)
    raise RuntimeError(f'Could not download {url}: {last_error}')


def sha256_file(file: Path) -> str:
    result = hashlib.sha256()
    with file.open('rb') as src:
        for chunk in iter(lambda: src.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def inspect_tarball(file: Path, expected_root: str) -> int:
    """Read the archive index without extracting files or following tar links."""
    member_count = 0
    cmake_found = False
    with tarfile.open(file, 'r:xz') as src:
        for member in src:
            member_count += 1
            if member.name.startswith('/') or '..' in Path(member.name).parts:
                raise RuntimeError(f'Unsafe member in {file.name}: {member.name}')
            if not (member.name == expected_root or member.name.startswith(expected_root + '/')):
                raise RuntimeError(f'Unexpected source root in {file.name}: {member.name}')
            if member.name == expected_root + '/CMakeLists.txt':
                cmake_found = True
    if member_count < 10 or not cmake_found:
        raise RuntimeError(f'Source tree looks incomplete: {file.name}; CMakeLists={cmake_found}, files={member_count}')
    return member_count


def prepare(destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    validated = []
    for index, info in enumerate(ARCHIVES, start=1):
        filename = info['name']
        target = destination / filename
        print(f'[{index}/{len(ARCHIVES)}] {filename}', flush=True)
        if not target.exists():
            with tempfile.NamedTemporaryFile(prefix='.download_', dir=destination, delete=False) as temp:
                temp_path = Path(temp.name)
            try:
                download(info['url'], temp_path)
                if temp_path.stat().st_size != info['size']:
                    raise RuntimeError(f'Size mismatch: {filename}: got {temp_path.stat().st_size}, expected {info["size"]}')
                got = sha256_file(temp_path)
                if got != info['sha256']:
                    raise RuntimeError(f'SHA-256 mismatch: {filename}: got {got}; expected {info["sha256"]}')
                os.replace(temp_path, target)
            finally:
                temp_path.unlink(missing_ok=True)
        if target.stat().st_size != info['size']:
            raise RuntimeError(f'Size mismatch: {filename}')
        if sha256_file(target) != info['sha256']:
            raise RuntimeError(f'SHA-256 mismatch: {filename}')
        root = filename.removesuffix('.tar.xz')
        count = inspect_tarball(target, root)
        print(f'  OK, {info["size"]:,} bytes, {count:,} tar members; SHA256 {info["sha256"]}', flush=True)
        validated.append({**info, 'archive_member_count': count, 'verification': 'SHA256+size+archive_structure_passed'})

    (destination / 'SHA256SUMS.txt').write_text(
        ''.join(f'{item["sha256"]}  {item["name"]}\n' for item in validated), encoding='utf-8')
    (destination / 'SOURCE_MANIFEST.json').write_text(
        json.dumps({'project': 'Kanyx', 'qt_version': '6.12.0', 'pyside6_version': '6.12.0',
                    'packages': validated, 'notes': [
                        'Archive checksums verified against metadata published by the Qt project.',
                        'No claim is made that these upstream archives alone are complete corresponding source for a specific wheel or binary.',
                        'Check build configuration, toolchain, packaging patches and bundled third-party libraries before distribution.',
                    ]}, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    (destination / 'README_SOURCES.txt').write_text('''Kanyx v1.0.0 - Candidate Qt 6.12.0 / PySide6 6.12.0 source archives

These independent source downloads are OPTIONAL for users running Kanyx.
They are made available to assist with LGPLv3 corresponding-source obligations.
The MIT license of Kanyx does NOT change the licenses of the bundled libraries.

Contents: official Qt source archives for qtbase, qtsvg, qtimageformats,
qtwayland (Linux), and pyside-setup (PySide6/shiboken6). Exact upstream
checksums and download URLs are in SOURCE_MANIFEST.json.

IMPORTANT: This archive is a preliminary source set. Before declaring an
LGPL-compliant release, the distributor must confirm it provides all source
and build/install information necessary for the LGPL-covered binaries shipped,
including any Qt-for-Python wheel patches and bundled third-party code.
See https://www.qt.io/development/open-source-lgpl-obligations
and https://www.gnu.org/licenses/lgpl-3.0.html
''', encoding='utf-8')
    print(f'All {len(validated)} archives verified. Output: {destination}', flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='dist/Kanyx-Qt-sources-6.12.0',
                        help='Directory with sources and manifest; upload as a separate release asset ZIP')
    parser.add_argument('--list', action='store_true', help='Print metadata without downloading')
    args = parser.parse_args()
    if args.list:
        print(json.dumps(ARCHIVES, indent=2))
        return 0
    prepare(Path(args.output))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        sys.exit(1)
