# Third-party components and license notices

Kanyx application source is licensed under MIT (see [`LICENSE`](LICENSE)). The MIT license does **not** relicense its dependencies.

## Qt for Python / PySide6 / shiboken6 / Qt 6

Kanyx uses the open-source distribution of PySide6 and Qt. The core components used by Kanyx are generally provided under **GNU LGPL version 3** (or alternative licenses). Individual Qt modules, plugins, and bundled components may use other licenses. Check the *actual distributable build*, its included libraries, Qt plugins, and their license metadata before publishing.

Copyright in Qt, PySide6, shiboken6, and third-party components remains with their respective copyright holders.

- [Qt for Python licensing](https://doc.qt.io/qtforpython-6/commercial/index.html)
- [Qt open-source obligations](https://www.qt.io/development/open-source-lgpl-obligations)
- [Qt licensing and third-party components](https://doc.qt.io/qt-6/licensing.html)
- LGPLv3 legal text: [`licenses/LGPL-3.0.txt`](licenses/LGPL-3.0.txt)
- GPLv3 legal text (incorporated by LGPLv3): [`licenses/GPL-3.0.txt`](licenses/GPL-3.0.txt)

### Binary distribution

Our recommended published binary is a **PyInstaller onedir** package. Its bundled Qt libraries are separate files, making replacement with compatible modified builds more practical than in a single executable. You must not prohibit reverse engineering needed to debug modifications of the LGPL-covered parts. Publishing source code for Kanyx does not alone satisfy all Qt LGPL distribution duties.

The distributor is responsible for providing the **complete corresponding source** of the exact LGPL-covered Qt/PySide6 libraries used (including any changes), either alongside the binaries or through a compliant written offer **under the distributor's control**. Merely linking to Qt's website or an upstream repository is **not sufficient** according to Qt's guidance. See [`docs/RELEASE_COMPLIANCE.md`](docs/RELEASE_COMPLIANCE.md) for a required release checklist.

### Other dependencies

PyInstaller is a **build-time tool**, with its own license and bootloader terms. Python and various bundled runtime components, libraries, plugins and transitive dependencies also have their own licenses. Collect a dependency/bundle inventory and include all required notices for the *exact versions distributed*. This document is an initial notice, **not a complete verified dependency inventory**.

## Kanyx icon and images

The project's MIT LICENSE does not automatically prove that third-party or generated assets are free of third-party rights. The maintainer must confirm rights to redistribute the current `assets/kanyx.png` and `assets/kanyx.ico`, including under the repository's chosen terms.
