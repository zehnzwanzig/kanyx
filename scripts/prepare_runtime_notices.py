#!/usr/bin/env python3
"""Record runtime-native files and package a verified CPython license.

Release helper; intentionally does *not* claim legal-compliance certification.
Uses only Python's standard library. Must run from the Python environment
that was used to freeze Kanyx, after PyInstaller and before bundle auditing.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import sqlite3
import ssl
import sys
import urllib.request
from pathlib import Path

# Both source tags have the same upstream LICENSE blob. Git blob hash obtained
# from the official python/cpython repository. Do not silently accept changes.
SUPPORTED_LICENSE_BLOBS = {
    '3.12.10': 'f26bcf4d2de6eb136e31006ca3ab447d5e488adf',
    '3.12.15': 'f26bcf4d2de6eb136e31006ca3ab447d5e488adf',
}


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(f'blob {len(data)}\0'.encode('ascii') + data).hexdigest()


def get_python_license(version: str, override: Path | None = None) -> tuple[bytes, str]:
    expected = SUPPORTED_LICENSE_BLOBS.get(version)
    if not expected:
        raise ValueError(f'Unreviewed Python version {version}; update the license pins before building')
    candidates = [Path(sys.base_prefix) / 'LICENSE.txt', Path(sys.base_prefix) / 'LICENSE']
    if override:
        candidates.insert(0, override)
    for path in candidates:
        if path.is_file():
            content = path.read_bytes()
            if git_blob_sha(content) == expected:
                return content, f'local:{path}'
    url = f'https://raw.githubusercontent.com/python/cpython/v{version}/LICENSE'
    req = urllib.request.Request(url, headers={'User-Agent': 'Kanyx-release-license-collector/1.0'})
    with urllib.request.urlopen(req, timeout=35) as response:
        content = response.read(100000)
    if git_blob_sha(content) != expected:
        raise ValueError('Python LICENSE integrity check failed: refusing to package unexpected content')
    return content, url


def is_native_library(name: str) -> bool:
    base = Path(name).name.lower()
    return base.endswith(('.dll', '.pyd', '.so', '.dylib', '.exe')) or '.so.' in base


def describe_native_files(bundle: Path) -> list[dict]:
    result = []
    for path in sorted(p for p in bundle.rglob('*') if p.is_file() and is_native_library(p.name)):
        relative = path.relative_to(bundle).as_posix()
        lowered = relative.lower()
        if 'pyside6/' in lowered and ('qt6' in lowered or '/plugins/' in lowered):
            group = 'Qt/Qt-plugin'
        elif 'shiboken6' in lowered or ('pyside6/' in lowered and (lowered.endswith('.pyd') or '.so' in lowered)):
            group = 'PySide6/Shiboken6'
        elif 'libssl' in lowered or 'libcrypto' in lowered:
            group = 'OpenSSL'
        elif 'python' in lowered or relative.endswith('/_sqlite3.pyd'):
            group = 'CPython/runtime-extension'
        else:
            group = 'Other native dependency (manual review)'
        result.append({'path': relative, 'size_bytes': path.stat().st_size, 'group': group})
    return result


def package_version(distribution: str) -> str | None:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path, help='PyInstaller onedir output folder')
    parser.add_argument('--python-license-file', type=Path, default=None,
                        help='Optional verified local source; used for offline builds')
    args = parser.parse_args()
    bundle = args.bundle.resolve()
    if not bundle.is_dir():
        parser.error(f'not a release directory: {bundle}')
    version = platform.python_version()
    data, provenance = get_python_license(version, args.python_license_file)
    licpath = bundle / 'licenses' / 'Python-3.12-LICENSE.txt'
    licpath.parent.mkdir(parents=True, exist_ok=True)
    licpath.write_bytes(data)
    manifest = {
        'status': 'EVIDENCE_ONLY_NOT_A_LEGAL_CLEARANCE',
        'python_version': version,
        'python_implementation': platform.python_implementation(),
        'python_license_reference': f'python/cpython tag v{version}: LICENSE',
        'python_license_origin': provenance,
        'python_license_git_blob_sha1': git_blob_sha(data),
        'openssl_version_used_by_python_ssl': ssl.OPENSSL_VERSION,
        'sqlite_version_used_by_python_sqlite3': sqlite3.sqlite_version,
        'pyside6_essentials_version': package_version('PySide6_Essentials'),
        'shiboken6_version': package_version('shiboken6'),
        'pyinstaller_version': package_version('pyinstaller'),
        'native_files': describe_native_files(bundle),
        'open_items': [
            'Manually verify all embedded third-party components and attribution/NOTICE texts.',
            'Map exact Qt/PySide6/Shiboken6 binaries to complete corresponding sources.',
            'Confirm any OpenSSL NOTICE and platform-runtime redistribution obligations.',
            'Perform modified LGPL-library replacement test and document its result.',
        ],
    }
    (bundle / 'RUNTIME_COMPONENTS.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Python license pinned and packaged: v{version}, {len(data)} bytes')
    print(f'Runtime components inventoried: {len(manifest["native_files"])}; manual attribution review still needed.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
