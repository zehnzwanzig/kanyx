# Kanyx v1.0.0-rc.1 — Practical Test Checklist

**Target:** Windows x64 and Linux x64  
**Project:** [Kanyx](https://github.com/zehnzwanzig/kanyx)  
**Release:** [v1.0.0-rc.1](https://github.com/zehnzwanzig/kanyx/releases/tag/v1.0.0-rc.1)  
**Purpose:** Validate the actual downloadable portable builds on real target environments, not just the automated unit tests.

> **Important — test data only.** Use a fresh, disposable copy of the application. Do not use your normal workspace or the original USB-stick installation. Workspace import replaces the active workspace; save a full `.kanyx` export before destructive tests.

## How to use this checklist

- Check a box **only when the expected behavior was observed**. If a test fails, leave it unchecked and record the result in the issue log below.
- **P0** = release blocker (cannot launch, data loss, broken export/import, inaccessible files). **P1** = major regression (core feature unusable). **P2** = cosmetic or minor inconvenience.
- Use the **actual release ZIPs**, not a Python development environment. Prefer clean Windows 11 x64 and Ubuntu 24.04 x64; add other supported environments as available.
- Perform the same functional tests on **both platforms**, even if automated CI tests pass.
- The Linux build is **experimental** until tested on a real machine or a VM with a desktop session.
- Never upload real databases, private attachments, or screenshots containing personal information to public GitHub Issues.

### Test environment

| Field | Windows | Linux |
|---|---|---|
| Tester / date | | |
| OS and exact version | | |
| Architecture | x64 | x64 |
| Physical machine or VM | | |
| Display / desktop session | Resolution, scaling | Resolution, X11 or Wayland |
| Installation path | | |
| USB/filesystem (if tested) | | |
| Build ZIP | `Kanyx-v1.0.0-rc.1-windows-x64.zip` | `Kanyx-v1.0.0-rc.1-linux-x64-experimental.zip` |
| ZIP SHA-256 verified against release | Yes / No | Yes / No |
| Test result | Not started / Pass / Fail | Not started / Pass / Fail |

### Prepare a reproducible test workspace

Create a new board named `QA – Kanyx` with columns `To Do`, `In Progress`, and `Done`. Add at least two cards, for example `Prepare release` and `Check backup`, with the tag `qa`, a priority, a due date, a 2-item checklist, and **small, non-sensitive** sample attachments (a `.txt` and a `.png`). Keep these as reference data throughout testing. Use a royalty-free image for any wallpaper tests.

---

## A. Windows x64 — installation and portability

- [ ] **W01 · P0 — ZIP extraction.** Download the published Windows ZIP and extract the **entire `Kanyx/` folder**, including `_internal/`. No files are missing.
- [ ] **W02 · P0 — Clean start.** `Kanyx.exe` launches on a Windows system **without a separate Python/Qt installation** and without administrator rights.
- [ ] **W03 · P0 — Data directory.** On first use, `Kanyx/data/` and `data/kanyx.db` are created next to the EXE, on a writable location; the footer shows the expected path.
- [ ] **W04 · P1 — Window behavior.** Move, resize, minimize, maximize/restore, and close the frameless window without UI glitches.
- [ ] **W05 · P1 — Display scaling.** Test at 100% and 125% or 150% Windows display scaling; buttons and dialogs remain reachable.
- [ ] **W06 · P1 — Paths.** Run from a folder with spaces and non-ASCII characters (e.g. `Kanyx Test Übung`). Creating and saving data works.
- [ ] **W07 · P0 — Offline.** Disconnect internet access, reopen the program and use an existing board. No cloud service or login is required.
- [ ] **W08 · P0 — Reopen.** Close Kanyx normally, relaunch, and verify that boards, cards, settings, and attachments persist.
- [ ] **W09 · P0 — Portable USB.** Copy the **complete application folder** to a writable USB stick, run from that stick, change a card and reopen it after safely ejecting/reconnecting.
- [ ] **W10 · P0 — Transfer.** Move the full folder (including `data/`) to another writable Windows location or machine; all content stays available.
- [ ] **W11 · P0 — Update preservation.** Export a backup; copy the `data/` folder into a fresh extracted application directory; launch and verify that no workspace data was lost. Do **not** overwrite `data/` with an empty folder.
- [ ] **W12 · P2 — Unsigned binary.** Record any SmartScreen/security warning as an expected unsigned-build limitation; do not disable organizational security controls to force a test.

## B. Linux x64 — installation and portability

- [ ] **L01 · P0 — Environment.** Record distribution/version, CPU architecture, desktop environment and whether the session uses **X11 or Wayland**.
- [ ] **L02 · P0 — ZIP extraction.** Download and extract the entire `Kanyx-linux/` directory to a writable local Linux filesystem.
- [ ] **L03 · P0 — Executable bit.** In the extracted folder run `chmod +x Kanyx-linux`, then `./Kanyx-linux`.
- [ ] **L04 · P0 — GUI launch.** Main window opens successfully without Python or PySide6 separately installed. Record errors if any.
- [ ] **L05 · P0 — Qt/XCB dependency.** On X11, verify the window starts; if it fails, investigate `libxcb-shape.so.0` and Qt platform-plugin errors. Do not mark passed merely because GitHub Actions built the package.
- [ ] **L06 · P1 — Wayland.** If a Wayland session is available, launch and check opening, dialogs, input and drag & drop. Note whether Qt used Wayland or XWayland.
- [ ] **L07 · P1 — Window and scaling.** Resize/minimize/maximize and check on HiDPI or fractional scaling if available; dialogs are fully visible.
- [ ] **L08 · P0 — Write access.** On a writable local directory, Kanyx creates `data/kanyx.db`, attachments, backups and wallpaper files as needed.
- [ ] **L09 · P0 — Offline.** Disconnect the network; application and saved workspace remain usable.
- [ ] **L10 · P0 — Persistence.** Close, restart and verify all test data and appearance settings remain intact.
- [ ] **L11 · P0 — Portable relocation.** Move the **entire** extracted directory (including `data/`) to another writable location; saved data still works.
- [ ] **L12 · P1 — Removable media.** Test a USB stick. Check file permissions and whether the filesystem/mount uses `noexec`. If `noexec`, record the limitation and test from an executable local directory instead. Moving the directory also moves the workspace path.
- [ ] **L13 · P0 — Update preservation.** In a fresh extract, restore the saved `data/` directory and verify cards and attachments remain accessible.
- [ ] **L14 · P1 — Filename handling.** Test spaces, umlauts and Japanese characters in folder paths and sample attachment names.

**Linux diagnostic command (only if launching fails):**

```bash
cd /path/to/Kanyx-linux
QT_DEBUG_PLUGINS=1 ./Kanyx-linux 2>&1 | tee kanyx-startup.log
```

Check errors about `xcb`, `libxcb-shape.so.0`, Wayland plugins, glibc or missing system libraries. Review logs for usernames and file paths before attaching them to an issue.

---

## C. Functional regression — run once on EACH platform

Tick the Windows and Linux tests separately. The scenarios intentionally cover the actual Kanyx UI and data model.

### F01 · P0 — Create and select boards

Create `QA – Kanyx` and another board; switch between them; titles and contents belong to the correct board.

- [ ] **Windows** — pass
- [ ] **Linux** — pass

### F02 · P1 — Board management

Rename a board and duplicate it; verify copied columns and cards. Delete only a disposable board after confirming the warning.

- [ ] **Windows** — pass
- [ ] **Linux** — pass

### F03 · P1 — Board templates

Create a board from a template and inspect its preset columns.

- [ ] **Windows** — pass
- [ ] **Linux** — pass

### F04 · P1 — Column management

Create a column, rename it, collapse/expand it and reorder columns using their drag handles.

- [ ] **Windows** — pass
- [ ] **Linux** — pass

### F05 · P0 — Create and edit cards

Add a card, rename it, write a multiline description, save, close and reopen; contents are unchanged.

- [ ] **Windows** — pass
- [ ] **Linux** — pass

### F06 · P0 — Card drag & drop

Move a card between `To Do`, `In Progress` and `Done`, reorder it within a column; order persists after restart.

- [ ] **Windows** — pass
- [ ] **Linux** — pass

### F07 · P1 — Priorities and dates

Set a non-default priority and a due date; verify both are retained and displayed.

- [ ] **Windows** — pass
- [ ] **Linux** — pass

### F08 · P1 — Colors and tags

Set a card color and multiple comma-separated tags; reopen and check the values.

- [ ] **Windows** — pass
- [ ] **Linux** — pass

### F09 · P1 — Checklist

Add two checklist items, rename one, check one complete, remove one; the remaining content persists.

- [ ] **Windows** — pass
- [ ] **Linux** — pass

### F10 · P1 — Markdown source and preview

Enter headings, bold text and a list; toggle Markdown preview, save and reopen. The raw Markdown source is not corrupted.

- [ ] **Windows** — pass
- [ ] **Linux** — pass

### F11 · P0 — Attach files

Attach a small `.txt` and `.png`, reopen the card and open both; the files are stored in `data/attachments/`.

- [ ] **Windows** — pass
- [ ] **Linux** — pass

### F12 · P1 — Attachment removal

Remove one attachment from a disposable card; it is no longer listed, while unrelated attachments remain intact.

- [ ] **Windows** — pass
- [ ] **Linux** — pass

### F13 · P1 — Duplicate card

Duplicate a card with tags, checklist and attachment; both cards remain usable. Editing/deleting a duplicate must not corrupt the original attachment.

- [ ] **Windows** — pass
- [ ] **Linux** — pass

### F14 · P1 — Archive and restore

Archive a card; it disappears from the active board and can be restored through **Archive**.

- [ ] **Windows** — pass
- [ ] **Linux** — pass

### F15 · P1 — Search

Search by card title, description text and tag; results update correctly and clearing search restores all cards.

- [ ] **Windows** — pass
- [ ] **Linux** — pass

### F16 · P1 — Priority filter

Filter by priority and reset to **All**; expected cards return.

- [ ] **Windows** — pass
- [ ] **Linux** — pass

### F17 · P1 — Undo/redo

Test `Ctrl+Z`, `Ctrl+Shift+Z` and `Ctrl+Y` on a **supported** operation (e.g. a card move). Do not assume every action is undoable.

- [ ] **Windows** — pass
- [ ] **Linux** — pass

### F18 · P1 — Keyboard shortcuts

Check `Ctrl+N`, `Ctrl+Shift+N`, `Ctrl+F`/`Ctrl+L`, `Esc`, and `Ctrl+1`/`2`/`3` (if corresponding boards exist).

- [ ] **Windows** — pass
- [ ] **Linux** — pass

### F19 · P1 — Appearance settings

Change wallpaper brightness, column opacity and UI scaling; check that settings take effect and persist.

- [ ] **Windows** — pass
- [ ] **Linux** — pass

### F20 · P1 — Wallpaper

Apply a non-sensitive wallpaper, relaunch and confirm it loads; remove it and verify removal.

- [ ] **Windows** — pass
- [ ] **Linux** — pass

### F21 · P1 — Language switching

Switch between English, German and at least one other supported language; existing user-created board/card names remain unchanged.

- [ ] **Windows** — pass
- [ ] **Linux** — pass

### F22 · P0 — Complete workspace export

Use **Workspace → Export workspace** to create a `.kanyx` archive; ensure it is nonempty and includes test attachments and wallpaper.

- [ ] **Windows** — pass
- [ ] **Linux** — pass

### F23 · P0 — Import cancellation

Start an import, choose **No/Cancel** at the replacement warning; current workspace must remain unchanged.

- [ ] **Windows** — pass
- [ ] **Linux** — pass

### F24 · P0 — Complete workspace import

In a **disposable** workspace, import the exported `.kanyx` file. Verify boards, cards, tags, checklists, attachments and wallpaper match the export.

- [ ] **Windows** — pass
- [ ] **Linux** — pass

### F25 · P0 — Import rollback evidence

After successful import, verify the previous workspace was retained as a rollback folder outside the active `data/` directory.

- [ ] **Windows** — pass
- [ ] **Linux** — pass

### F26 · P0 — Corrupt import rejection

Try importing a deliberately damaged *copy* of a `.kanyx` export. It must fail without modifying the current workspace.

- [ ] **Windows** — pass
- [ ] **Linux** — pass

### F27 · P0 — Database backup

Use **Workspace → Create database backup**. Check that a nonempty SQLite backup appears in `data/backups/`.

- [ ] **Windows** — pass
- [ ] **Linux** — pass

### F28 · P0 — Data integrity

Use **Workspace → Check data integrity** after normal editing and an import. No missing-file errors should appear.

- [ ] **Windows** — pass
- [ ] **Linux** — pass

### F29 · P0 — Restart persistence

Fully close the app and relaunch; compare the saved board structure, card details and file attachments against the expected test data.

- [ ] **Windows** — pass
- [ ] **Linux** — pass

### F30 · P1 — Delete confirmation

Delete a disposable card and verify the confirmation prompt. Cancel once; only confirm deletion in a separate test.

- [ ] **Windows** — pass
- [ ] **Linux** — pass

### F31 · P1 — Many cards and scrolling

Add enough cards to require scrolling in one column; the list, controls and dragging remain usable.

- [ ] **Windows** — pass
- [ ] **Linux** — pass

### F32 · P1 — No interference from other boards

Edit cards on board A, switch to board B and return; board B is unaffected.

- [ ] **Windows** — pass
- [ ] **Linux** — pass

---

## D. Extra release/negative tests

### Windows

- [ ] **W13 · P0 — Missing file failure is controlled.** On a *disposable copy only*, rename `_internal/` temporarily, try launching, and confirm that the app fails clearly rather than silently damaging `data/`. Restore the folder afterward.
- [ ] **W14 · P1 — Read-only location.** Test on a disposable read-only location; record whether failure is understandable and whether a previously saved workspace remains safe.
- [ ] **W15 · P1 — Multiple launches.** Check accidental second launch using the same workspace; **simultaneous multi-instance use is not supported**. Record actual behavior, avoid editing from both instances.

### Linux

- [ ] **L15 · P1 — Qt plugin diagnostics.** If the GUI does not start, save `QT_DEBUG_PLUGINS=1` output and classify the problem (missing OS library, plugin path, glibc, display server).
- [ ] **L16 · P1 — Desktop integration.** Test file dialogs, opening an attached file with the system default application and window close behavior.
- [ ] **L17 · P1 — Second environment.** If possible, test on another desktop or distribution and document any dependencies rather than assuming universal portability.

## E. Evidence and issue reporting

**For each failure:** include test ID, platform, OS version, ZIP filename, exact reproduction steps, expected result, actual result, and a sanitized screenshot or log. Report reproducible bugs at [GitHub Issues](https://github.com/zehnzwanzig/kanyx/issues/new/choose).

| Test ID | OS / environment | Priority | Actual result / reproduction | GitHub issue URL | Fixed and retested? |
|---|---|---|---|---|---|
| | | | | | |
| | | | | | |
| | | | | | |
| | | | | | |

## F. Final acceptance decision

- [ ] All **P0** tests passed on Windows.
- [ ] All **P0** tests passed on Linux, **or** Linux remains explicitly labeled **experimental / unverified**.
- [ ] No confirmed data loss, data corruption, or irreversible workspace-import failure.
- [ ] All outstanding P1/P2 issues have been recorded with reproducible steps.
- [ ] Windows portable USB use and full-folder migration have been tested on a clean machine.
- [ ] Linux GUI boot and critical desktop dependencies have been verified before removing the experimental label.
- [ ] The published release files and their SHA-256 hashes match the versions actually tested.
- [ ] Remaining Qt/LGPL and third-party binary-distribution obligations have been separately reviewed before claiming legal release readiness. This checklist validates functionality, **not** legal compliance.

### Test summary

| Platform | Passed | Failed | Not tested | Recommendation |
|---|---:|---:|---:|---|
| Windows | | | | Go / No-go |
| Linux | | | | Go / Experimental / No-go |

**Tester:**  
**Test date:**  
**Release under test:** `v1.0.0-rc.1`  
**Overall decision and notes:**

---

### Notes on known limitations

- Windows releases are **unsigned**; SmartScreen may warn even when the executable is legitimate. Verify that the ZIP was downloaded from the official GitHub release.
- Linux may require `libxcb-shape.so.0` and other desktop/system libraries; an automated build passing does not establish runtime compatibility.
- A database-only backup **does not include** attachments and wallpapers; use `.kanyx` export for complete portable backups.
- Avoid writing to the same workspace from two concurrent Kanyx instances.
- A workspace import **replaces** the active workspace, although a rollback copy should be retained. Always test import with disposable data.
