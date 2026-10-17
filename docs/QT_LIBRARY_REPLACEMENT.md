# Replacing Qt/PySide6 shared libraries in Kanyx v1.0.0

**Status: documented layout; an actual modified-library replacement test is still outstanding.**

Kanyx's application source is MIT-licensed. Its bundled Qt 6.12.0,
PySide6-Essentials 6.12.0 and shiboken6 6.12.0 retain their respective
licenses, including LGPL-3.0 where applicable. Read `THIRD_PARTY_NOTICES.md`,
`licenses/LGPL-3.0.txt`, `licenses/GPL-3.0.txt` and
`docs/THIRD_PARTY_SOURCES.md`.

Kanyx uses a **PyInstaller `--onedir` build**, not a monolithic statically linked Qt executable. The files listed below were verified in the Windows and Linux candidate artifacts from GitHub Actions *Build release candidates #2* (run `39045916104`). Do not assume this guide applies unchanged to later versions.

## Compatibility and precautions

- Replace files **in a disposable copy** of the extracted application folder, not in the original download or an existing user workspace.
- Replacement builds must be compatible with **Qt 6.12.0**, the same architecture (64-bit), platform, and the Python/PySide6 ABI; matching names alone do **not** guarantee compatibility.
- Do not mix incompatible Qt release/debug binaries or replace a library with an unrelated or differently configured module.
- Qt plugins may need corresponding replacement when changing a Qt library. Keep the plugin directory tree intact.
- No administrator privileges, proprietary signing keys or activation server should be required by Kanyx to use interface-compatible replacement libraries. OS security or native library requirements may still apply.
- If a modified build does not launch, restore the original files. Breakage from an incompatible binary is not evidence that compatible replacement is prohibited.

## Windows (candidate from run 39045916104)

Qt shared libraries:

```text
Kanyx.exe
_internal/PySide6/Qt6Core.dll
_internal/PySide6/Qt6Gui.dll
_internal/PySide6/Qt6Network.dll
_internal/PySide6/Qt6Svg.dll
_internal/PySide6/Qt6Widgets.dll
_internal/PySide6/plugins/...
_internal/shiboken6/shiboken6.abi3.dll
```

To test an **ABI-compatible, independently built** replacement such as `Qt6Svg.dll`, open PowerShell and work in a separate test copy:

```powershell
Copy-Item -Recurse -Path .\Kanyx -Destination .\Kanyx-qt-test
Copy-Item -Path 'C:\path\to\modified\Qt6Svg.dll' `
  -Destination '.\Kanyx-qt-test\_internal\PySide6\Qt6Svg.dll' -Force
.\Kanyx-qt-test\Kanyx.exe
```

Change the source path to the actual DLL you built. The example is **not a completed successful test**: it documents the replacement location and procedure. To investigate plugin loading, launch from a terminal with `QT_DEBUG_PLUGINS=1` set in the environment.

## Linux (candidate from run 39045916104)

The Linux candidate contains the same Qt `.so.6` libraries in **two locations**:

```text
Kanyx-linux
_internal/libQt6Svg.so.6
_internal/PySide6/Qt/lib/libQt6Svg.so.6
_internal/PySide6/Qt/plugins/...
_internal/shiboken6/libshiboken6.abi3.so.6.12
```

Both copies of each duplicated library were byte-identical in the candidate inventory. **Until the runtime search order is tested, replace both copies** when testing a compatible modified Qt shared library:

```bash
cp -a Kanyx-linux Kanyx-linux-qt-test
cp /path/to/modified/libQt6Svg.so.6 \
  Kanyx-linux-qt-test/_internal/libQt6Svg.so.6
cp /path/to/modified/libQt6Svg.so.6 \
  Kanyx-linux-qt-test/_internal/PySide6/Qt/lib/libQt6Svg.so.6
chmod +x Kanyx-linux-qt-test/Kanyx-linux
QT_DEBUG_PLUGINS=1 ./Kanyx-linux-qt-test/Kanyx-linux
```

Run this inside a disposable test directory. A modified library must retain a compatible soname/ABI and its own dependencies. Linux portability also depends on the system's loader, GLIBC, display server and related libraries.

## Required maintainer validation before releasing binaries

- [ ] Produce a minimal, visibly modified but ABI-compatible Qt 6.12.0 shared library from corresponding sources (e.g. a QtSvg rebuild).
- [ ] Replace the real library in the **Windows** candidate; verify that the modified library is loaded and the application launches and operates normally.
- [ ] Repeat on **Linux**, with both copies replaced; confirm the effective library loading path.
- [ ] Record build instructions, environment/toolchain versions, runtime logs and test results with the release evidence.
- [ ] Audit other bundled LGPL components (PySide6, Shiboken6) and any additional necessary installation/relinking information.
- [ ] Confirm that the corresponding source offering is complete and durably accessible **before** publication of binary releases.

This documentation describes the current packaging layout. It is **not legal certification** or proof of replaceability until an actual compatible-modified-library test is completed.

## Authoritative references

- Qt open-source obligations: https://www.qt.io/development/open-source-lgpl-obligations
- LGPL v3 section 4 (combined works): https://www.gnu.org/licenses/lgpl-3.0.en.html
