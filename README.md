# Kanyx 1.0.0

**A minimalist, portable, offline-first Kanban board for Windows and Linux.**

Built with **Python, PySide6 (Qt 6) and SQLite**. No accounts, cloud service or network connection required. Designed for a single workspace on a USB stick.

## Features

- Boards, reorderable/collapsible columns, draggable task cards
- Tags, priorities, due dates, checklists, attachments, archive and duplication
- Markdown description preview, card colors, checklist progress, board templates
- Search, keyboard shortcuts and session undo/redo for selected operations
- Custom wallpaper, adjustable brightness/column opacity/text size
- Six UI languages: English (default), German, Spanish, French, Japanese, Korean
- Complete `.kanyx` workspace export/import with attachment files; database backups and integrity checks

## Windows – run the portable executable

Download the `Kanyx.exe` artifact from a release/build made on Windows. Put it next to a `data/` directory on a writable USB stick (the application creates `data/` automatically on first run). Run `Kanyx.exe`; target machines do not need a separate Python or Qt installation.

> Windows SmartScreen or corporate security policies may warn about unsigned executables. This repository does not provide code signing.

## Linux – run the portable executable

Download a Linux build produced on a compatible Linux distribution. Make it executable with `chmod +x Kanyx-linux`, then run `./Kanyx-linux`. **Linux portability is not guaranteed across all distributions**: libc/Qt desktop dependencies and `noexec` USB mounts can prevent execution. If your stick is mounted `noexec`, copy the executable to an executable local directory while keeping workspace data backed up; a different data directory will be used unless the executable remains next to the original `data/` folder.

## Run from source

Python 3.11+ recommended for development (other versions may work). From the project directory:

```bash
python -m venv .venv
# Activate your virtual environment according to your OS
python -m pip install -r requirements.txt
python main.py
```

On Windows you may run `.venv\Scripts\python.exe main.py` without activating the environment.

## Build locally

For public-release candidates use `scripts\build_windows_release.bat` on Windows or `bash scripts/build_linux_release.sh` on Linux. These create folders with separate Qt libraries and legal notice texts.

- Windows: `scripts\build_windows.bat` → `dist\Kanyx.exe`
- Linux: `bash scripts/build_linux.sh` → `dist/Kanyx-linux`

**Cross-compilation is not supported by these scripts**; build each executable on its respective operating system.

## Portable workspace, updates and backups

Kanyx stores its database, attachments, wallpapers and backups in `data/` **next to the running executable** (or next to `db.py` when run from source). Keep `data/` when updating to a newer executable. Older `data/pyban.db` databases are recognized; don't rename or remove them without making a backup.

Use **Workspace → Export workspace** to write a full `.kanyx` backup (includes attachments). **Import workspace replaces the entire current workspace**, and creates a rollback copy of the previous data folder. A database-only backup does *not* include attachments. Exported workspaces are **not encrypted**.

Do not use the same workspace simultaneously from multiple instances. A multi-instance lock is intentionally not implemented.

## Tests and releases

```bash
python -m unittest discover -s tests -v
```

CI runs unit tests on Windows and Linux. Pushing a tag like `v1.0.0` invokes the build workflow and uploads Windows/Linux **onedir candidate folders** as GitHub Actions artifacts. These are **not automatically published as a GitHub Release**; the maintainer should test them and then upload them to a release manually.

See [CHANGELOG.md](CHANGELOG.md), [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), and [previous version documentation](docs/HISTORY_AND_FEATURES.md).

## Known limitations

- Single-user offline workspace; no cloud sync or multi-user collaboration.
- Undo/redo does not cover every editor operation or permanent deletion.
- Interface scaling adjusts text; not all controls scale proportionally.
- Linux builds depend on the target desktop and libraries. Real-world GUI testing is required on target operating systems.

## License and redistribution

Kanyx's own source code is under the [MIT License](LICENSE). **PySide6/Qt and other dependencies are separately licensed.** Read [third-party notices](THIRD_PARTY_NOTICES.md) and the [release compliance checklist](docs/RELEASE_COMPLIANCE.md) before publishing any executable packages. The generic copyright notice currently in `LICENSE` must be confirmed by the maintainer.

For public binary releases prefer the **onedir** scripts `scripts/build_windows_release.bat` and `scripts/build_linux_release.sh`; distribute each entire resulting folder as a ZIP, **not just the executable**. The older `build_windows.bat` and `build_linux.sh` continue to create single-file executables for local experimentation; they are not the recommended public binary format. The LGPL compliance checklist still requires an exact binary license audit and corresponding-source provision before release.
