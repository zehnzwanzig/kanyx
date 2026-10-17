#!/usr/bin/env python3
"""Produce a reproducible, scoped native-linkage report for Kanyx artifact ZIPs.

Requires GNU binutils 'objdump' and 'readelf' (e.g. Ubuntu).
Reads selected ELF/PE binaries directly from the ZIPs, without executing them.
This is evidence for review, NOT an SPDX/SBOM or a license-compliance certificate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from zipfile import ZipFile

WINDOWS_FILES = [
    '_internal/_hashlib.pyd',
    '_internal/PySide6/plugins/tls/qopensslbackend.dll',
    '_internal/PySide6/Qt6Network.dll',
    '_internal/libcrypto-3.dll',
    '_internal/libcrypto-3-x64.dll',
    '_internal/libssl-3-x64.dll',
]
LINUX_FILES = [
    '_internal/PySide6/Qt/plugins/platforms/libqxcb.so',
    '_internal/PySide6/Qt/lib/libQt6XcbQpa.so.6',
    '_internal/PySide6/Qt/plugins/tls/libqopensslbackend.so',
    '_internal/PySide6/Qt/lib/libQt6Network.so.6',
    '_internal/libssl.so.3',
    '_internal/libcrypto.so.3',
    '_internal/libgssapi_krb5.so.2',
]


def check_tools():
    tools = ('objdump', 'readelf')
    unavailable = [tool for tool in tools if shutil.which(tool) is None]
    if unavailable:
        raise RuntimeError(f'Missing required binutils: {", ".join(unavailable)}')


def inspect_zip(path: Path, filenames: list[str], platform: str) -> dict:
    result = {'platform': platform, 'artifact': path.name,
              'artifact_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
              'libraries': [], 'note': 'Static import tables omit libraries loaded at runtime.'}
    with ZipFile(path, 'r') as bundle:
        names = set(bundle.namelist())
        missing = sorted(set(filenames)-names)
        if missing:
            raise ValueError(f'{path}: expected files missing: {missing}')
        for filename in filenames:
            data = bundle.read(filename)
            with tempfile.TemporaryDirectory(prefix='kanyx_linkage_') as td:
                target = Path(td) / Path(filename).name
                target.write_bytes(data)
                args = ['objdump', '-p', str(target)] if platform == 'Windows' else ['readelf', '-d', str(target)]
                completed = subprocess.run(args, capture_output=True, text=True, timeout=35, check=True)
            if platform == 'Windows':
                deps = re.findall(r'^\s*DLL Name:\s*(\S+)', completed.stdout, re.M)
            else:
                deps = re.findall(r'\(NEEDED\).*?\[([^\]]+)\]', completed.stdout)
            result['libraries'].append({'path': filename, 'size_bytes': len(data),
                                        'sha256': hashlib.sha256(data).hexdigest(),
                                        'imported_libraries': sorted(set(deps), key=str.lower)})
        if platform == 'Linux':
            all_basenames = {Path(x).name for x in names if '/' in x}
            qpa_names = set()
            for item in result['libraries']:
                if 'libqxcb.so' in item['path'] or 'libQt6XcbQpa.so.6' in item['path']:
                    qpa_names.update(item['imported_libraries'])
            result['qpa_imports_not_in_archive'] = sorted(x for x in qpa_names if x not in all_basenames)
            result['important_note'] = ('These may exist on the target OS; absence from the archive alone '
                                        'does not establish a runtime failure.')
        else:
            runtime = [x for x in names if re.search(r'(?:^|/)(?:MSVCP140(?:_\d+)?|VCRUNTIME140(?:_\d+)?|ucrtbase|api-ms-win-[^/]+)\.dll$', x, flags=re.I)]
            result['packaged_microsoft_runtime_files'] = sorted(runtime)
            result['important_note'] = ('Visual C++ Redistributable licensing and allowed distribution '
                                        'must be verified from Microsoft terms and upstream wheel provenance.')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--windows', type=Path, required=True, help='Windows candidate Actions ZIP')
    parser.add_argument('--linux', type=Path, required=True, help='Linux candidate Actions ZIP')
    parser.add_argument('--out', type=Path, required=True, help='JSON evidence report path')
    a = parser.parse_args()
    check_tools()
    obj = {'schema_version': 1, 'status': 'EVIDENCE_ONLY_NO_LEGAL_CLEARANCE',
           'windows': inspect_zip(a.windows, WINDOWS_FILES, 'Windows'),
           'linux': inspect_zip(a.linux, LINUX_FILES, 'Linux')}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
    print('Wrote', a.out)
    for key in ('windows', 'linux'):
        print(key, len(obj[key]['libraries']), 'selected native binaries inspected')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
