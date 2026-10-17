# OpenSSL binary inventory for Kanyx build #4

**Status:** release evidence; NOT a full third-party license clearance.

- Run: https://github.com/zehnzwanzig/kanyx/actions/runs/39055418349
- Commit: `4028fb9ca2bf0802619e5644f9f352304418a931`
- Date: 2026-10-17
- Source: Windows and Linux `Kanyx-*-candidate` ZIP contents.
- SHA-256: computed on the uncompressed binary bytes in the ZIP.
- Version identification: embedded OpenSSL version string found in `libcrypto`; this does not alone prove provenance or the version of associated `libssl` binaries.

| Platform | File in package | Bytes | SHA-256 | Version evidence |
|---|---|---:|---|---|
| Windows | `_internal/libcrypto-3-x64.dll` | 7,144,080 | `cc15784f3aea86a526fa3d74e1fe1df94293e96d0888fbaacf4ed9f8e24ea2e0` | 3.5.5 (binary string) |
| Windows | `_internal/libcrypto-3.dll` | 5,231,472 | `ccfffddcd3defb8d899026298af9af43bc186130f8483d77e97c93233d5f27d7` | 3.0.16 (binary string) |
| Windows | `_internal/libssl-3-x64.dll` | 1,314,952 | `6de9ca3242fb130ee489f22cdef58f48b458afdc9636ca9c9c6ed57a921408d9` | not independently verified |
| Windows | `_internal/PySide6/plugins/tls/qopensslbackend.dll` | 317,752 | `94b3492bc4087da2818e2749a5a03f7d810611b2e3648bd8d580ad087363046f` | Qt TLS plugin |
| Linux | `_internal/libcrypto.so.3` | 5,309,400 | `6866ed711dab8927e1bf82bf1cd30e828bdfc34f3cc1e83b1c9eb01ce6c37d9a` | 3.0.13 (binary string) |
| Linux | `_internal/libssl.so.3` | 696,512 | `a40e7b67489bbd257e432c700ff8f6a1ad796425b5eccecdc2930127fdd86624` | not independently verified |
| Linux | `_internal/PySide6/Qt/plugins/tls/libqopensslbackend.so` | 363,104 | `d6f153ea607720b1ea08fb66d224be3c012d5023cee983a22735ae11c03709d2` | Qt TLS plugin |

## Versions observed

- Windows Python reports `OpenSSL 3.0.16 11 Feb 2025`, but another bundled DLL advertises **3.5.5**. Determine the respective consumers and dependencies before assuming either is redundant.
- Linux Python reports `OpenSSL 3.0.13 30 Jan 2024`.
- The separately bundled `libk5crypto.so.3` on Linux is a **Kerberos** library and should not be conflated with OpenSSL; its own licensing is still to be audited.
- `qopensslbackend.dll` / `libqopensslbackend.so` are Qt TLS plugins and do not share the OpenSSL project's license merely by referring to OpenSSL.
- The package contains `licenses/Apache-2.0.txt`; do not treat that alone as evidence that all runtime components have been reviewed.

## Open release gates

- [ ] Determine library provenance (Python distribution vs PySide6/Qt vs build-runner), ownership and exact dependency linkage, especially both Windows libcrypto versions.
- [ ] Confirm exact license obligations for these OpenSSL distributions, including any required NOTICE files or extra third-party components.
- [ ] Audit Linux's Kerberos libraries and other bundled system libraries separately.
- [ ] Ensure all required license texts and notices appear in the distributable.
- [ ] Regenerate this evidence for the final release build if any binary changes.

Official OpenSSL license sources:
- https://github.com/openssl/openssl/blob/openssl-3.0.13/LICENSE.txt
- https://github.com/openssl/openssl/blob/openssl-3.0.16/LICENSE.txt
- https://github.com/openssl/openssl/blob/openssl-3.5.5/LICENSE.txt
