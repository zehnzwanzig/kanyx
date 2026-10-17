# Kanyx v1.0.0 — OpenSSL and Qt third-party license evidence

**Review status: IN PROGRESS, NOT APPROVED FOR PUBLIC BINARY DISTRIBUTION.**

Evidence: GitHub Actions `Build release candidates #3`, run `39051484170`.
This document records inspected archive entries, NOT a complete bill of materials.

## OpenSSL

| Evidence | Windows | Linux |
|---|---|---|
| Reported by bundled CPython's `ssl.OPENSSL_VERSION` | OpenSSL 3.0.16 | OpenSSL 3.0.13 |
| OpenSSL shared libraries | `_internal/libcrypto-3-x64.dll`, `_internal/libcrypto-3.dll`, `_internal/libssl-3-x64.dll` | `_internal/libcrypto.so.3`, `_internal/libssl.so.3` |
| Applicable license for OpenSSL 3.x | Apache-2.0 | Apache-2.0 |
| License in bundle | `licenses/Apache-2.0.txt` | `licenses/Apache-2.0.txt` |

**Important:** the `ssl` value reports the library linked to Python's SSL module; it does not establish the build origin or exact version of **every** OpenSSL DLL present in the Windows package. Inspect the binaries themselves and verify any vendor-specific notices and/or differences. OpenSSL licensing: <https://openssl-library.org/source/license/index.html>.

## Qt image plugins and supplementary native components

| Component or plugin | Windows | Linux | Documentation source |
|---|---|---|---|
| TIFF plugin | `_internal/PySide6/plugins/imageformats/qtiff.dll` | `_internal/PySide6/Qt/plugins/imageformats/libqtiff.so` | https://doc.qt.io/qt-6/qtimageformats-attribution-libtiff.html |
| WebP plugin | `_internal/PySide6/plugins/imageformats/qwebp.dll` | `_internal/PySide6/Qt/plugins/imageformats/libqwebp.so` | https://doc.qt.io/qt-6/qtimageformats-attribution-libwebp.html |
| JPEG plugin | `_internal/PySide6/plugins/imageformats/qjpeg.dll` | `_internal/PySide6/Qt/plugins/imageformats/libqjpeg.so` | https://doc.qt.io/qt-6/qtgui-attribution-libjpeg.html |
| ICU (separate runtime) | no matching libicu*.dll found | `libicudata.so.73`, `libicui18n.so.73`, `libicuuc.so.73` (duplicated in two locations) | Review separate ICU distribution terms |
| FreeType, HarfBuzz, PNG (separate runtime) | no matching DLLs found | `libfreetype.so.6`, `libharfbuzz.so.0`, `libpng16.so.16` | Qt Core/GUI attributions and Linux package license sources |

The presence of Qt plugins does not establish whether every codec is bundled internally or linked from the OS. For this reason the source-verified notice files are included conservatively, while the exact embedded/system linkage remains a manual review item.

## Added build safeguards

`scripts/prepare_qt_third_party_notices.py` retrieves seven original attribution files from official Qt GitHub source trees **tagged `v6.12.0`**, verifies Git blob hashes, and copies them into each binary candidate under `licenses/third-party/`.
It generates `THIRD_PARTY_QT_NOTICES.md` and `THIRD_PARTY_QT_MANIFEST.json` in the distribution folder. The manifest contains the immutable origin path and the verification result. Build failures abort on unavailable or changed upstream notices. Offline build: provide the verified files in `--cache-dir`.

## Still blocking public release

- [ ] Verify Windows OpenSSL DLL provenance, versions, required notices.
- [ ] Confirm license attribution of Linux ICU and other bundled system libraries (glib, fontconfig, libdbus, pcre2, brotli, zstd, sqlite, etc.).
- [ ] Review complete Qt 6.12 `qtbase`, `qtsvg`, `qtimageformats` and `qtwayland` SBOM / third-party sources; the seven pinned notices are a *subset*.
- [ ] Verify relevant Python and PyInstaller third-party notice requirements and package ownership.
- [ ] Confirm Qt/PySide6/Shiboken6 complete corresponding sources including build information (not merely upstream links).
- [ ] Verify replacement with a compatible user-modified LGPL-covered library on Windows and Linux.
- [ ] Perform a genuine Linux application functionality test, or mark Linux experimental if publication proceeds after legal review.
- [ ] Make all corresponding sources and notices durably available with any published binary.

Further guidance: https://doc.qt.io/qt-6/licenses-used-in-qt.html and `docs/RELEASE_COMPLIANCE.md`.
