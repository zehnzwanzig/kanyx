# Kanyx 1.0.0 — runtime third-party review (pre-release)

**Status: OPEN — not a legal clearance.** The Kanyx program remains MIT licensed;
shipping binary libraries requires satisfying each component's own terms.

## Evidence: Build release candidates #2

GitHub Actions: https://github.com/zehnzwanzig/kanyx/actions/runs/39045916104

| Component | Windows | Linux | Status |
| --- | --- | --- | --- |
| Python runtime | CPython **3.12.10** | CPython **3.12.15** | Include the full version-matched Python `LICENSE` |
| Qt / PySide6-Essentials / Shiboken6 | **6.12.0** | **6.12.0** | LGPL-source and module notices still require validation |
| PyInstaller bootloader | **6.22.3** | **6.22.3** | Bootloader exception reference in existing notices |
| OpenSSL | `libcrypto-3-x64.dll`, `libcrypto-3.dll`, `libssl-3-x64.dll` | `libcrypto.so.3`, `libssl.so.3` | Apache-2.0 text already included; exact OpenSSL version/NOTICE still to review |
| SQLite | `sqlite3.dll`, `_sqlite3.pyd` | `libsqlite3.so.0`, `_sqlite3*.so` | Check supplied runtime and provenance; SQLite core is public-domain |
| Qt image format plugins | `qtiff.dll`, `qwebp.dll`, `qjpeg.dll` | `libqtiff.so`, `libqwebp.so`, `libqjpeg.so` | Attribute embedded libtiff/libwebp and verify other image components |
| Windows Microsoft runtime | bundled `MSVCP140.dll`, `VCRUNTIME140*.dll` etc. | not applicable | Check Microsoft redistribution terms and origin |
| Linux system libraries | not applicable | ICU, PNG, JPEG, GLib/loader-related libraries, etc. | Complete provenance and license inventory outstanding |

The new `scripts/prepare_runtime_notices.py` collects the full CPython license
from a *version-pinned, Git-blob-verified* official source if a verified local
LICENSE cannot be found. It writes `licenses/Python-3.12-LICENSE.txt` and
`RUNTIME_COMPONENTS.json` inside **each** candidate package. The latter provides
audit evidence, not license clearance. Builds fail for an unexpected CPython
patch version so the Python LICENSE cannot silently go stale.

## Outstanding manual checks

- [ ] Review `RUNTIME_COMPONENTS.json` from both **fresh** builds.
- [ ] Verify OpenSSL version and notices independently, including whether the OpenSSL source package contains a NOTICE file that must be reproduced.
- [ ] Get exact third-party license text for `libtiff`, `libwebp`, image plugins and Qt dependency tree from Qt 6.12.0 sources / SPDX SBOM; do not infer embedded code solely from a plugin filename.
- [ ] Verify Microsoft redistributable DLL rights and the Linux system-library origins.
- [ ] Demonstrate substituting an ABI-compatible modified LGPL Qt library (Windows; Linux when testable).
- [ ] Confirm source packages and build information are **complete corresponding source** for the binaries actually shipped, and make them durable release assets.
- [ ] Have the maintainer complete the release license review before publicly distributing binary candidates.

## References

- CPython 3.12 license: https://docs.python.org/3.12/license.html
- Official CPython source tags: https://github.com/python/cpython/tags
- OpenSSL 3 license: https://openssl-library.org/source/license/index.html
- Qt 6.12 third-party components: https://doc.qt.io/qt-6/licenses-used-in-qt.html
- PyInstaller bootloader license: https://pyinstaller.org/en/stable/license.html
- LGPL obligations: https://www.qt.io/development/open-source-lgpl-obligations
