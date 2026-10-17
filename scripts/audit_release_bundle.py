#!/usr/bin/env python3
"""Pre-release *risk screening*, not a legal compliance certificate.

Audit a PyInstaller onedir directory or an Actions ZIP. Exit nonzero for known
GPL-only Qt modules and missing mandatory notice files. Stdlib-only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from zipfile import ZipFile

REQUIRED = {
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
    "licenses/LGPL-3.0.txt",
    "licenses/GPL-3.0.txt",
    "licenses/Apache-2.0.txt",
}

# Known GPL-only Qt modules (under the Qt community/open-source distribution).
# Not exhaustive: consult the licensing documents for the exact Qt version.
GPL_ONLY_FRAGMENTS = (
    "virtualkeyboard", "qt6graphs", "qt6grpc", "qt6httpserver", "qt6mqtt",
    "qt6coap", "qt6networkauth", "qt6lottie", "qt6quick3d",
    "qt6waylandcompositor", "qt6quicktimeline", "qt6canvaspainter",
)


def scan(path: Path) -> dict:
    if path.is_dir():
        names = [p.relative_to(path).as_posix() for p in path.rglob('*') if p.is_file()]
    elif path.is_file() and path.suffix.lower() == '.zip':
        with ZipFile(path) as z:
            names = [n for n in z.namelist() if not n.endswith('/')]
    else:
        raise ValueError('Expected an extracted onedir folder or a ZIP artifact')

    lower_names = [n.lower() for n in names]
    present = set(names)
    # Some ZIP producers wrap the payload in an outer folder. Recognize that form.
    missing = sorted(p for p in REQUIRED if not any(n == p or n.endswith('/' + p) for n in names))
    flagged = sorted(n for n in names if
                     n.lower().endswith(('.dll', '.so', '.dylib', '.pyd'))
                     or '.so.' in n.lower() if any(s in n.lower() for s in GPL_ONLY_FRAGMENTS))
    qt_binaries = sorted(n for n in names if ('qt6' in n.lower() or 'shiboken6' in n.lower())
                         and (n.lower().endswith(('.dll', '.pyd', '.dylib', '.so')) or '.so.' in n.lower()))
    openssl = sorted(n for n in names if any(s in Path(n).name.lower() for s in ('libcrypto', 'libssl')))
    pdf = sorted(n for n in names if 'qt6pdf' in Path(n).name.lower())

    return {
        'bundle': str(path), 'files': len(names), 'qt_binaries': qt_binaries,
        'gpl_only_risks': flagged, 'missing_notices': missing,
        'openssl_binaries': openssl, 'qt_pdf_binaries': pdf,
        'result': 'BLOCK' if flagged or missing else 'PRELIMINARY_PASS',
        'note': ('PRELIMINARY_PASS does not certify LGPL/GPL/third-party compliance. '
                 'Manual review, replaceability and corresponding source obligations remain.'),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    parser.add_argument('--report', type=Path, help='Save a JSON audit inventory')
    args = parser.parse_args()
    try:
        result = scan(args.bundle)
    except (OSError, ValueError) as exc:
        print(f'Audit failed: {exc}', file=sys.stderr)
        return 2
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f"Release screen: {result['result']} ({result['files']} files)")
    if result['gpl_only_risks']:
        print('GPL-only module candidates (must remove or separately resolve licensing):')
        for name in result['gpl_only_risks']:
            print('  -', name)
    if result['missing_notices']:
        print('Missing license files:', ', '.join(result['missing_notices']))
    if result['qt_pdf_binaries']:
        print('Notice: Qt PDF found; audit PDFium / its bundled third-party notices.')
    if result['openssl_binaries']:
        print('Notice: OpenSSL binaries found; audit the applicable OpenSSL license notices.')
    if result['result'] == 'PRELIMINARY_PASS':
        print('GPL-only module screen passed. Complete the manual release compliance checklist.')
        return 0
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
