# Third-party components and license notices

Kanyx application source code is available under the [MIT License](LICENSE). That license **does not relicense the libraries** bundled with an executable.

## Qt for Python / PySide6-Essentials / Shiboken6 / Qt 6

Kanyx uses the Qt for Python bindings, Qt runtime libraries and plugins. For the open-source distribution, PySide6 and Shiboken6 are available under LGPLv3/GPLv3 alternatives, and individual Qt modules have their own license terms. Copyright remains with their respective owners, including The Qt Company Ltd. and Qt contributors.

- LGPL version 3: [`licenses/LGPL-3.0.txt`](licenses/LGPL-3.0.txt)
- GPL version 3, whose terms are incorporated by LGPLv3: [`licenses/GPL-3.0.txt`](licenses/GPL-3.0.txt)
- Licensing guide: https://doc.qt.io/qt-6/licensing.html
- LGPL obligations: https://www.qt.io/development/open-source-lgpl-obligations
- Qt for Python licensing: https://doc.qt.io/qtforpython-6/commercial/index.html

Under the applicable LGPL provisions, recipients must be able to modify and replace the LGPL-covered Qt libraries with compatible versions and debug those changes. Kanyx uses PyInstaller **onedir** release candidates with separately distributed Qt libraries. Kanyx source code is available in this repository; the distributor must additionally arrange access to **complete corresponding source code** of the actual LGPL-covered Qt/PySide6/Shiboken6 versions distributed, including applicable changes and build information, or use a legally sufficient distributor-controlled source offer. A bare upstream link does not by itself fulfill Qt's stated source-code distribution expectations.

**Known issue in first build, 2026-10-17:** Both initial Windows and Linux artifacts bundled Qt Virtual Keyboard, which Qt lists as GPLv3-only for open-source distribution. These bundles are **not approved for public release**. The amended build uses PySide6-Essentials and an automated screening step to keep known GPL-only modules out of future candidate packages. A passing automated screen is *not* a full legal compliance review.

## OpenSSL

Builds may bundle OpenSSL 3.x libraries (for example `libssl` and `libcrypto`). OpenSSL 3 and later versions derived from it are distributed under the **Apache License, Version 2.0**. See [`licenses/Apache-2.0.txt`](licenses/Apache-2.0.txt) and https://openssl-library.org/source/license/index.html. Verify the exact OpenSSL version, any included NOTICE files, and the actual libraries before releasing.

## CPython and Python standard-library components

PyInstaller includes Python runtime and standard-library code in frozen applications. These components have license obligations independent of Kanyx's MIT license, including the Python Software Foundation license stack and notices for third-party code included in Python. The distributor must verify and include the relevant license texts for the Python version actually bundled.

- Python license FAQ: https://wiki.python.org/moin/PythonSoftwareFoundationLicenseFaq
- Python licensing: https://docs.python.org/3/license.html

Release packages include `licenses/Python-3.12-LICENSE.txt`, copied from a
version-matched official CPython source tag and verified against a pinned Git
blob digest, and `RUNTIME_COMPONENTS.json` containing a native-binary inventory.
These are supporting evidence, not a complete third-party license audit. See
`docs/RUNTIME_THIRD_PARTY_REVIEW.md` in the repository for open items.

## PyInstaller

PyInstaller is licensed under GPL-2.0-or-later with a bootloader exception allowing the distribution of generated executables under the application license, subject to dependency licensing requirements. Using PyInstaller does not automatically make Kanyx GPL-licensed.

- License and bootloader exception: https://pyinstaller.org/en/stable/license.html

## Other runtime libraries and Qt dependencies

Qt modules may embed third-party software; for example Qt PDF includes PDFium and multiple additional licenses. Other Qt plugins, the Microsoft C/C++ runtime, SQLite and packaged system libraries should be inventoried and their exact redistributable terms verified. This document is a starting notice, **not a complete inventory or proof of compliance**.

## Kanyx icon and artwork

The maintainer must confirm the right to distribute all icons, images and generated artwork in the project, including `assets/kanyx.png` and `assets/kanyx.ico`.

Before any public binary release, see the repository documentation: https://github.com/zehnzwanzig/kanyx/blob/main/docs/RELEASE_COMPLIANCE.md and https://github.com/zehnzwanzig/kanyx/blob/main/docs/LICENSE_AUDIT_2026-10-17.md.
