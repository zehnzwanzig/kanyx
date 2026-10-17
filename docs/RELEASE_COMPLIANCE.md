# Public Release: compliance and publishing checklist

**Not legal advice.** This is a technical release checklist. Verify current requirements and the exact licenses of all shipped modules before distribution.

## 1. Attribution and repository

- [ ] Confirm the rightful copyright owner(s) and replace the generic `Kanyx contributors` notice in `LICENSE` if appropriate. Commit the unmodified MIT license terms.
- [ ] Confirm rights to distribute the source and icon/artwork under the chosen terms.
- [ ] Keep `LICENSE` at repository root and include it in all downloadable distributions.
- [ ] Link `THIRD_PARTY_NOTICES.md` from README and include it in binary archives.

## 2. Qt / PySide6 LGPLv3 obligations

- [ ] Determine the exact versions and license options for PySide6, shiboken6, Qt modules, plugins and Qt's third-party code shipped in **each** binary; some Qt modules are GPL-only or have special licensing.
- [ ] Distribute the relevant LGPLv3 and GPLv3 license texts and required third-party notices.
- [ ] Prefer dynamic Qt DLL/shared-library linkage and preserve users' ability to replace those libraries with compatible modified versions. Test a replacement or document the procedure; avoid locks, signing requirements or EULA restrictions that prohibit it.
- [ ] Provide **complete corresponding source code** for the shipped LGPL-covered components, including the original sources, applied patches if any, and required build information. Under Qt's stated policy, **an upstream URL alone is not enough**: host the exact source on a controlled release asset/mirror or make an appropriate legally compliant written offer under your control.
- [ ] Include instructions needed to replace/relink with a compatible modified version. For cases involving installation information requirements, ensure the necessary information is provided.
- [ ] Do not introduce extra restrictions on modifying/reverse engineering LGPL-covered components for debugging modifications.
- [ ] Confirm license and notice obligations for Python, PyInstaller bootloader, system runtime components and other transitive dependencies actually included in each build.

## 3. Technical release gates

- [ ] Build on Windows and Linux separately from a pinned, reviewed dependency environment; record `pip freeze` and binary contents.
- [ ] Inspect the built `dist/Kanyx/` or `dist/Kanyx-linux/` for Qt shared libraries and third-party plugins.
- [ ] Test launch, data-folder creation, cards, attachments, `.kanyx` import/export, and shutdown on clean target machines without Python installed.
- [ ] Test USB stick write access and correct retention of `data/` next to the launcher, including an upgrade from v0.9.
- [ ] Check Linux glibc, Qt platform plugin dependencies and executable bit after extracting ZIP; note `noexec` USB mount caveats.
- [ ] Preserve private `data/` folders outside tracked git content. Ensure release archives never contain personal workspace files.
- [ ] Manually upload verified binary ZIPs and corresponding compliance materials to the GitHub Release.

## 4. Recommended release workflow

1. Create the repository, commit code, verify license owner and asset rights.
2. Run CI. Create tag `v1.0.0` only when ready.
3. Download Windows/Linux **onedir** artifacts from GitHub Actions.
4. Audit their contents and make Qt/PySide6 corresponding-source packages available as release assets or suitable distributor-controlled written offers.
5. Smoke-test clean machines, then publish a GitHub Release with the packages and license/source materials.

**Do not publish these artifacts as LGPL-compliant solely on the strength of the bundled notice files: the exact binary inventory and corresponding-source provision remain outstanding.**
