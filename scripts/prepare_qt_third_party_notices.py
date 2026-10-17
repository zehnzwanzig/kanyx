#!/usr/bin/env python3
"""Add source-verified Qt third-party notices to a PyInstaller onedir package.

Uses official Qt v6.12.0 source files and checks their immutable Git blob IDs.
This covers a REVIEWED SUBSET of Qt's third-party dependencies; it is NOT a
complete software bill of materials or legal compliance certification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from dataclasses import dataclass
from pathlib import Path

QT_TAG = 'v6.12.0'


@dataclass(frozen=True)
class Attribution:
    filename: str
    repository: str
    path: str
    git_blob_sha1: str
    component: str
    context: str


# All hashes obtained from Qt's official GitHub source mirrors at v6.12.0.
NOTICES = (
    Attribution('libtiff-COPYRIGHT.txt', 'qt/qtimageformats',
                'src/3rdparty/libtiff/COPYRIGHT',
                '8282186151e224ac83d9990805062ff7b8effa00',
                'libtiff', 'Qt TIFF image-format plugin'),
    Attribution('libwebp-COPYING.txt', 'qt/qtimageformats',
                'src/3rdparty/libwebp/COPYING',
                '7a6f99547d4d6b4c5e6d5321acfaeba313e08de3',
                'libwebp', 'Qt WebP image-format plugin'),
    Attribution('libjpeg-turbo-LICENSE.txt', 'qt/qtbase',
                'src/3rdparty/libjpeg/LICENSE',
                '37a489b245eeb16c9ad8fae217b54f07ca00a65c',
                'libjpeg-turbo', 'Qt JPEG image-format plugin'),
    Attribution('libjpeg-IJG-LICENSE.txt', 'qt/qtbase',
                'src/3rdparty/libjpeg/ijg-license.txt',
                'eec5341d1c4e9ded532479684d061ffe3f6915b2',
                'Independent JPEG Group', 'Qt JPEG image-format plugin'),
    Attribution('libpng-LICENSE.txt', 'qt/qtbase',
                'src/3rdparty/libpng/LICENSE',
                '1b765ae9f96abea77d3d9a88c543e3b5f4725813',
                'libpng', 'Qt image processing and/or Linux native libpng'),
    Attribution('harfbuzz-COPYING.txt', 'qt/qtbase',
                'src/3rdparty/harfbuzz-ng/COPYING',
                '1dd917e9f2e72167de69e3b5dadbc4e7db417da1',
                'HarfBuzz', 'Qt text shaping and/or Linux libharfbuzz'),
    Attribution('freetype-FTL.txt', 'qt/qtbase',
                'src/3rdparty/freetype/docs/FTL.TXT',
                'b9e8cbd66ffff526113350953f4a2f4252a92f49',
                'FreeType', 'Qt fonts and/or Linux libfreetype'),
)


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(f'blob {len(data)}\0'.encode('ascii') + data).hexdigest()


def source_url(item: Attribution) -> str:
    return f'https://raw.githubusercontent.com/{item.repository}/{QT_TAG}/{item.path}'


def verified_source(item: Attribution, cache_dir: Path | None = None) -> tuple[bytes, str]:
    # Optional cache for offline builds: files have the final notice filename.
    if cache_dir:
        cached = cache_dir / item.filename
        if cached.is_file():
            raw = cached.read_bytes()
            if git_blob_sha(raw) != item.git_blob_sha1:
                raise ValueError(f'Invalid cached source Git blob: {item.filename}')
            return raw, str(cached)
    url = source_url(item)
    request = urllib.request.Request(url, headers={'User-Agent': 'Kanyx-third-party-notices/1.0'})
    with urllib.request.urlopen(request, timeout=40) as response:
        raw = response.read(200_000)
    if git_blob_sha(raw) != item.git_blob_sha1:
        raise ValueError(f'Unexpected upstream license contents: {item.filename}')
    return raw, url


def write_notices(bundle: Path, cache_dir: Path | None = None) -> dict:
    if not bundle.is_dir():
        raise ValueError(f'Not a release folder: {bundle}')
    target = bundle / 'licenses' / 'third-party'
    target.mkdir(parents=True, exist_ok=True)
    items = []
    for item in NOTICES:
        raw, origin = verified_source(item, cache_dir=cache_dir)
        (target / item.filename).write_bytes(raw)
        items.append({
            'component': item.component, 'context': item.context,
            'notice_path': f'licenses/third-party/{item.filename}',
            'qt_source_tag': QT_TAG,
            'origin_repository': item.repository, 'origin_path': item.path,
            'origin_url': source_url(item),
            'git_blob_sha1': item.git_blob_sha1,
            'bytes': len(raw), 'downloaded_from': origin,
        })
        print(f'Verified: {item.filename} ({len(raw)} bytes)')
    manifest = {
        'status': 'VERIFIED_LICENSE_TEXTS_PARTIAL_ATTRIBUTION_NOT_LEGAL_CLEARANCE',
        'qt_version': '6.12.0',
        'method': 'Git blob SHA-1 of exact tagged Qt source file, NOT a legal-completeness assertion',
        'notices': items,
        'still_required': [
            'Review full Qt Core/GUI SBOM and which dependencies are embedded in each wheel.',
            'Review licensing and notices of bundled system libraries on Linux (ICU, glib, fontconfig, PCRE2, ...).',
            'Verify OpenSSL binary versions, vendor notices and any redistribution conditions.',
            'Prove LGPL complete-corresponding-source and compatible library replacement procedures.',
        ],
    }
    (bundle / 'THIRD_PARTY_QT_MANIFEST.json').write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    lines = [
        '# Qt 6.12.0 — third-party license notices (partial verified set)', '',
        'The notices in `licenses/third-party/` are unmodified files obtained from',
        'the Qt v6.12.0 source trees and verified against their Git blob IDs.',
        'These copyright and license texts remain the property of their authors.', '',
        '**This is not a complete binary license audit or release clearance.**', '',
        '| Component | Included notice |', '|---|---|',
    ]
    lines += [f'| {i["component"]} | `{i["notice_path"]}` |' for i in items]
    lines += [
        '', 'The build also includes the separate `licenses/Apache-2.0.txt`',
        'for OpenSSL 3.x where applicable; the packaged OpenSSL DLL/.so versions',
        'and any further notices must be checked independently.', '',
        'See `THIRD_PARTY_NOTICES.md` and `THIRD_PARTY_QT_MANIFEST.json`.',
        'See the project release compliance checklist before distributing.', '',
    ]
    (bundle / 'THIRD_PARTY_QT_NOTICES.md').write_text('\n'.join(lines), encoding='utf-8')
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    parser.add_argument('--cache-dir', type=Path, default=None,
                        help='Optional directory of license files for offline builds')
    args = parser.parse_args()
    try:
        m = write_notices(args.bundle, args.cache_dir)
    except (OSError, ValueError) as exc:
        parser.exit(2, f'Qt third-party attribution preparation FAILED: {exc}\n')
    print(f'Qt third-party notices verified: {len(m["notices"])} (partial inventory; further review required).')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
