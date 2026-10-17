# Kanyx v1.0.0 — Qt/PySide6 source distribution

**Status: PREPARATION ONLY — public binary release is not yet licensed/compliance-cleared.**

Kanyx is licensed under MIT. Its bundled Qt, PySide6 and shiboken6 components
have independent licensing terms (including LGPLv3). The official sources
listed below are **not** part of a normal Kanyx download. They should be
provided as a separate, independently accessible GitHub Release download
at the time any public binary is offered.

## Source versions and package mapping

| Package | Platforms | Why included |
| --- | --- | --- |
| `qtbase-everywhere-src-6.12.0.tar.xz` | Windows, Linux | QtCore, QtGui, QtWidgets, QtNetwork, platform plugins and other QtBase components |
| `qtsvg-everywhere-src-6.12.0.tar.xz` | Windows, Linux | QtSvg library / SVG plugins |
| `qtimageformats-everywhere-src-6.12.0.tar.xz` | Windows, Linux | TIFF, WebP and other image format plugins |
| `qtwayland-everywhere-src-6.12.0.tar.xz` | Linux | Wayland client libraries and plugins |
| `pyside-setup-everywhere-src-6.12.0.tar.xz` | Windows, Linux | Qt for Python's PySide6 and shiboken6 source tree |

Download directory for Qt components:
https://download.qt.io/official_releases/qt/6.12/6.12.0/submodules/

Download directory for PySide6:
https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.12.0-src/

`SOURCE_MANIFEST.json` in the generated source package records upstream
SHA-256 checksums, expected file sizes, platform mapping, and download URLs.
The workflow verifies both the archive hashes and the archive structure.

## Prepare the independent source package

1. Review `scripts/prepare_qt_sources.py` and its fixed metadata.
2. Run the GitHub Actions workflow **Prepare Qt source archives** from `main`.
3. Download its **Kanyx-Qt-sources-6.12.0** artifact, a ZIP containing the
   five intact upstream `.tar.xz` files, `SHA256SUMS.txt`, `SOURCE_MANIFEST.json`
   and `README_SOURCES.txt`.
4. Check archive contents and audit notes. Publish the ZIP as an *independent,
   durable GitHub Release asset* alongside—not inside—the application package.
5. Place the actual source-asset download location in the release notes and
   Qt/PySide6 notices. **A GitHub Actions artifact alone is not permanent
   source distribution.** Do not publish the binaries until the compliance
   items below are complete.

No source archives need to be committed to Git. The output defaults to `dist/`,
which the project `.gitignore` already excludes.

## Required validation still outstanding

- [ ] Confirm the released Qt/PySide6/Shiboken6 binaries correspond to these
  source archives; review packaging/build patches and generated binding code.
- [ ] Confirm complete corresponding source and necessary scripts/build and
  installation information for *all* distributed LGPL-covered components,
  including nested/upstream third-party components.
- [ ] Determine which source/archive subsets can legitimately be omitted (the
  five archives here are a reasoned starting point, not a final legal claim).
- [ ] Provide complete licensing and attribution for bundled Python, OpenSSL,
  Qt third-party libraries, plugins, PyInstaller bootloader, and platform runtimes.
- [ ] Verify that a compatible user-modified Qt shared library can be substituted
  and Kanyx still launches; document how, including Linux Qt duplicate copies.
- [ ] Conduct Linux GUI testing on a compatible system, or label Linux
  experimental/unverified.
- [ ] Add publicly accessible **permanent** source package to the same release
  before any binary is made available.

## Authoritative guidance

- LGPLv3: https://www.gnu.org/licenses/lgpl-3.0.html
- Qt LGPL obligations: https://www.qt.io/development/open-source-lgpl-obligations
- Qt Open Source FAQ: https://www.qt.io/faq/qt-open-source-licensing

This document provides a technical traceability and distribution workflow, not
legal certification. When in doubt, obtain legal review before public release.
