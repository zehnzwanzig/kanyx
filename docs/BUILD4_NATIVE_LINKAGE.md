# Kanyx 1.0.0 – native dependency evidence (Build #4)

**Status: technical evidence only; NOT CLEARED FOR PUBLIC BINARY RELEASE.**

- GitHub Actions: https://github.com/zehnzwanzig/kanyx/actions/runs/39055418349
- Build commit: `4028fb9ca2bf0802619e5644f9f352304418a931`
- Windows artifact: `Kanyx-Windows-candidate` (ZIP)
- Linux artifact: `Kanyx-Linux-candidate` (ZIP)
- Analysis: imported DLL names from PE import tables using GNU `objdump -p` and ELF `DT_NEEDED` using `readelf -d`.
- The accompanying JSON report includes SHA-256 of each selected binary and of each input artifact.
- **Limitation:** Native import tables do not enumerate all libraries loaded dynamically at runtime. File names alone do not prove provenance, exact license obligations, or compatibility.

## 1. Windows — OpenSSL dependency evidence

| Binary in release | Verified imported library | Meaning |
|---|---|---|
| `_internal/_hashlib.pyd` | `libcrypto-3.dll` | Python extension directly depends on this file. |
| `_internal/libssl-3-x64.dll` | `libcrypto-3-x64.dll` | Another distinct OpenSSL pair is directly linked. |
| `_internal/PySide6/plugins/tls/qopensslbackend.dll` | `Qt6Network.dll`, `Qt6Core.dll` (not libssl in static imports) | Qt TLS backend is included; OpenSSL can be loaded dynamically, so an absent direct import is **not** evidence of non-use. |
| `_internal/PySide6/Qt6Network.dll` | Windows OS DLLs, QtCore, Visual C++ libraries | Qt networking library is present. |

The earlier version-string inspection identified `libcrypto-3.dll` as OpenSSL 3.0.16 and `libcrypto-3-x64.dll` as 3.5.5, but this **does not authenticate the upstream vendor/build**. The exact origin of these binaries and any vendor modifications still needs to be verified. Do not remove either pair just because Kanyx is an offline app: Qt or Python may still use these functions.

The OpenSSL 3 Apache-2.0 license text is present in the release. Determine whether the binaries originate in the official CPython runtime, the PySide6 wheel, or the Windows build image; preserve additional notices where applicable. **OpenSSL is not an LGPL component**, and its Apache-2.0 license does not automatically require an OpenSSL source archive.

Official: https://openssl-library.org/source/license/index.html

## 2. Windows — Microsoft redistributable runtime

The package includes MSVCP140, VCRUNTIME140 and Universal CRT/API-set DLLs. In this candidate, the audit enumerated **53 Microsoft-runtime-looking binary paths** (including API-set forwarding/stub DLLs); see the JSON file for exact paths.

Microsoft explains that redistribution of Visual C++ runtime DLLs is subject to its software license terms and its **REDIST** list, and that certain Visual Studio files cannot be redistributed. Therefore **do not assume PyInstaller packaging alone grants redistribution rights**. Confirm the origin, permissions and exact distribution method for the files shipped by Python/PySide6. Do not indiscriminately delete them, as the portable build depends on appropriate runtime availability.

References:
- https://learn.microsoft.com/cpp/windows/redistributing-visual-cpp-files
- https://learn.microsoft.com/cpp/windows/determining-which-dlls-to-redistribute

## 3. Linux — actual ELF dependencies

`_internal/PySide6/Qt/plugins/platforms/libqxcb.so` and `_internal/PySide6/Qt/lib/libQt6XcbQpa.so.6` require multiple `libxcb-*` components, including **`libxcb-shape.so.0`**. That name is **absent from the release ZIP**, consistent with the PyInstaller unresolved-library warning. The target host may supply it, but this must be documented and tested rather than assumed.

Other Qt XCB dependencies not contained in the ZIP include the following; many are commonly provided by the Linux host. Their absence from the archive alone is **not** a failure or license violation:

- `libGL.so.1`
- `libc.so.6`
- `libm.so.6`
- `libxcb-cursor.so.0`
- `libxcb-icccm.so.4`
- `libxcb-image.so.0`
- `libxcb-keysyms.so.1`
- `libxcb-render-util.so.0`
- `libxcb-shape.so.0`
- `libxcb-util.so.1`
- `libxcb-xkb.so.1`
- `libxcb.so.1`
- `libxkbcommon-x11.so.0`

The release also bundles *many* actual system-derived libraries inside `_internal/`, including GTK, X11, ICU, Kerberos, font handling and graphics libraries. The existing `RUNTIME_COMPONENTS.json` classified **95 Linux native files** as "Other native dependency (manual review)" (this group also includes duplicated Qt libraries). Those distributed binaries require their own origin/license review. The seven Qt third-party notice files do **not** cover all of these Linux system libraries.

`libQt6Network.so.6` directly imports `libgssapi_krb5.so.2`, which in turn imports `libkrb5.so.3`, `libk5crypto.so.3`, and related Kerberos libraries. **Kerberos `libk5crypto.so.3` is NOT the OpenSSL `libcrypto.so.3`.**

Qt XCB dependency documentation: https://doc.qt.io/qt-6/linux-requirements.html

**Recommendation:** Keep Linux marked *experimental / not yet distributed as official supported binary* until GUI execution and package dependency/license audit can be done on a compatible Linux installation.

## 4. Relevant technical results

| Test or source | Status |
|---|---|
| Windows Build #4 executable from USB | Reported working by maintainer. |
| Windows Qt6Core baseline load | `BASELINE_DLL_LOADED_AND_APP_STARTED` (from the maintainer's report; original Qt DLL copied, not source-modified). |
| Source archive workflow, Qt/PySide6 6.12.0 | Verified archives available as GitHub Actions artifact, but NOT yet a durable public source offering. |
| Native library import inspection | Completed for the selected PE/ELF files; results in JSON. |
| Substituting a genuinely source-modified LGPL-covered library | Not tested. |
| Comprehensive licensing for *all* distributed native libraries | Not completed. |
| Linux clean-environment GUI functional test | Not completed. |

## 5. Next explicit release gates

- [ ] **Windows**: Identify and document actual provenance and applicable licenses for each OpenSSL binary and the Microsoft runtime DLLs. Check the relevant REDIST entitlement.
- [ ] **Windows**: Finish any Qt/CPython/transitive third-party notices not covered by the seven reviewed Qt license files; review all externally bundled runtime assets.
- [ ] **Qt LGPL**: Establish complete corresponding-source offering under maintainer control, including matching generated bindings, relevant build information, and any patches; permanent source asset or legally adequate written offer.
- [ ] **Qt LGPL**: Ensure clear notice and workable compatible modified-library replacement/relink mechanism. The baseline load test is useful but is not a test of an independently modified library.
- [ ] **Linux**: Address missing XCB runtime dependencies, review native GTK/Kerberos/ICU/system libraries, and perform actual GUI smoke tests before offering official Linux support.
- [ ] After any changes, regenerate and compare manifests from the **final** binary build. Do not reuse this report as proof for binaries built from a different commit.

## 6. Reproduction (on Linux with GNU binutils)

Run from the repository root after placing the Windows and Linux Actions ZIPs outside of git-tracked paths:

```bash
python3 scripts/inspect_native_linkage.py \
  --windows /path/to/Kanyx-Windows-candidate.zip \
  --linux /path/to/Kanyx-Linux-candidate.zip \
  --out /tmp/Kanyx-native-linkage.json
```

This script makes **no changes to Kanyx or to the ZIPs**, and does not execute any binaries. It requires `objdump` and `readelf`. The script itself is not a legal license auditor.
