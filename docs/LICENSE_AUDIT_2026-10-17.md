# Kanyx v1.0.0 – third-party release audit (2026-10-17)

**Status: NOT CLEARED FOR PUBLIC BINARY RELEASE.** This is an evidence-driven technical inventory, not a legal opinion.

## Evidence reviewed

- Repository: https://github.com/zehnzwanzig/kanyx
- GitHub Actions run: https://github.com/zehnzwanzig/kanyx/actions/runs/39029081714
- Windows artifact: `Kanyx-Windows-candidate` (218 files; ~129.2 MB uncompressed)
- Linux artifact: `Kanyx-Linux-candidate` (338 files; ~309.0 MB uncompressed)
- Both archives contain project MIT LICENSE, THIRD_PARTY_NOTICES.md, GPL-3.0.txt and LGPL-3.0.txt.
- Workflow install log recorded PySide6 6.12.0, PySide6_Essentials 6.12.0, PySide6_Addons 6.12.0, shiboken6 6.12.0, PyInstaller 6.22.3. The full `PySide6` metapackage also fetched Qt PDF and Qt WebEngine package dependencies.

## Critical issue: Qt Virtual Keyboard (GPL-3.0-only option)

Windows includes:

- `_internal/PySide6/Qt6VirtualKeyboard.dll`
- `_internal/PySide6/plugins/platforminputcontexts/qtvirtualkeyboardplugin.dll`

Linux includes:

- `_internal/PySide6/Qt/lib/libQt6VirtualKeyboard.so.6`
- `_internal/PySide6/Qt/lib/libQt6VirtualKeyboardQml.so.6`
- `_internal/PySide6/Qt/plugins/platforminputcontexts/libqtvirtualkeyboardplugin.so`
- Plus duplicate copies of some Qt Virtual Keyboard shared libraries in `_internal/`.

Qt's public licensing guide lists Qt Virtual Keyboard as **GPLv3-only** among open-source licensing choices (no LGPL option). Since Kanyx's source is MIT, do not ship this binary package without a conscious full-license analysis. The lowest-risk approach is to remove the unused module and its plugins from the release candidate.

Source code reviewed (main.py, ui.py, db.py, portability.py, i18n.py) imports only PySide6.QtCore, QtGui and QtWidgets. No Kanyx import of Qt Virtual Keyboard was found. Runtime and transitive-dependency checks remain necessary.

## Additional identified components

- Windows includes `Qt6Pdf.dll` and Qt QML/Qt Quick libraries. Qt PDF brings PDFium and multiple separately licensed third-party components; inspect Qt PDF's notices if it remains in the final bundle.
- Both platforms include `libssl`/`libcrypto` libraries. OpenSSL 3.x is Apache-2.0-licensed. Verify which build and version is embedded and include the corresponding notices / license.
- Bundled CPython, Python standard library, SQLite, Microsoft runtime libraries, other Qt plugins and PyInstaller bootloader require an exact third-party attribution and redistribution audit.
- A PyInstaller `--onedir` bundle keeps Qt shared libraries as files that may be replaceable, but **filesystem visibility by itself does not establish full LGPLv3 compliance**. Verify loading, compatible replacement/relinking, license texts, and corresponding source obligations.

## Proposed remediation

1. Install only `PySide6-Essentials==6.12.0` plus `pyinstaller==6.22.3` in a **fresh virtual environment**.
2. Rebuild Windows and Linux from fresh GitHub Actions runners. Ensure the pre-release audit script exits with status 0 and that Qt Virtual Keyboard libraries/plugins are absent. It should be considered a risk *screen*, never a full compliance certificate.
3. Perform GUI regression testing on Windows and Linux; verify data persistence, drag/drop, board import/export and portable USB paths.
4. Inventory exact binaries, notices, and build versions. Gather Python PSF license stack, OpenSSL Apache-2.0 license/NOTICE if applicable, any Qt third-party license notices, and verify Microsoft runtime redistribution rights.
5. Make **complete corresponding source code** for the specific shipped LGPL-covered Qt/PySide6/Shiboken6 libraries available as required, including relevant build information and modifications. Do not rely solely on upstream URLs. The maintainer must control the source offer/accessibility in a compliant manner.
6. Demonstrate or document that interface-compatible modified Qt libraries can be substituted and that no terms restrict reverse engineering needed to debug their changes.
7. Only then promote candidates to a public GitHub Release.

## Official references

- Qt licensing (GPL-only modules): https://doc.qt.io/qt-6/licensing.html
- Qt Virtual Keyboard: https://doc.qt.io/qt-6/qtvirtualkeyboard-index.html
- Qt's LGPL obligations: https://www.qt.io/development/open-source-lgpl-obligations
- LGPL-3.0 §4: https://www.gnu.org/licenses/lgpl-3.0.en.html
- Qt for Python package details: https://doc.qt.io/qtforpython-6/package_details.html
- Qt for Python sources 6.12.0: https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.12.0-src/
- Qt 6.12.0 source downloads: https://download.qt.io/official_releases/qt/6.12/6.12.0/
- OpenSSL 3 license: https://openssl-library.org/source/license/index.html
- Python PSF license guidance: https://wiki.python.org/moin/PythonSoftwareFoundationLicenseFaq
- PyInstaller bootloader exception: https://pyinstaller.org/en/stable/license.html

## Sign-off

- [ ] GPL-only module check passes for **both** new bundles
- [ ] Windows functionality verified on clean machine
- [ ] Linux functionality verified on a compatible Linux environment
- [ ] Full binary list + dependency versions recorded
- [ ] Complete Qt/PySide6/Shiboken6 source access arranged under a compliant method
- [ ] Required license texts, OpenSSL/Python/Qt third-party attributions completed
- [ ] Shared-library replacement tested or otherwise confirmed with suitable evidence
- [ ] Release owner completes final license/compliance review
