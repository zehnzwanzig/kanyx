# Kanyx v0.9.0 – Portable Offline-Kanban-Anwendung

Kanyx (vormals **Pyban**) ist eine offline nutzbare Kanban-Desktopanwendung für Windows und Linux. Technischer Stack: Python 3, PySide6 (Qt 6), SQLite. Kostenloses Open-Source-Projekt.

## Funktionen

- Mehrere Boards und Spalten, mit Drag & Drop sortierbar
- Aufgaben mit Prioritäten, Fälligkeitsterminen, Tags, Checklisten und lokalen Dateianhängen
- Suche und Filter
- Dark Mode, eigene rahmenlose Titelleiste
- Eigenes Wallpaper (lokal gespeichert), einstellbare Helligkeit und Spaltendeckkraft
- UI-Skalierung von 80 % bis 140 % (Textgrößen); Darstellung über das Menü »Appearance«
- Automatische SQLite-Speicherung sowie Sicherungen beim Start
- Markdown-Kartentexte mit Vorschau (reiner Text in der Datenbank)
- Optionale Farbakzente pro Karte und sichtbarer Checklistenfortschritt
- Integrierte Board-Vorlagen (Einfach / Projekt / Persönlich / Leer)
- Tastaturkürzel und sechs UI-Sprachen
- Portable `.kanyx`-Workspace-Dateien (Import/Export inklusive Anhängen und Wallpaper)
- Prüfsummenvalidierung beim Import, SQLite-Integritätsprüfung und manuelle DB-Sicherungen

## Start aus dem Quellcode (Windows)

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

## Windows-EXE erstellen

In Windows-CMD (mit installiertem Python):

```bat
scripts\build_windows.bat
```

Ergebnis: `dist\Kanyx.exe`. Python oder Qt müssen auf dem Ziel-PC nicht installiert sein.

## Linux-Build

Auf einem Linux-Rechner mit Python 3:

```bash
bash scripts/build_linux.sh
```

Ergebnis: `dist/Kanyx-linux`. Linux-Kompatibilität und USB-Mountoptionen (`noexec`) hängen vom Zielsystem ab.

## Speicherort und Update von Pyban auf Kanyx

Alle persönlichen Daten bleiben im Verzeichnis `data/` **neben der ausführbaren Datei** (oder neben `main.py` beim Quellcodestart), einschließlich `attachments/`, `backups/` und `wallpapers/`.

**Für ein Update unbedingt den alten `data/`-Ordner beibehalten oder in das neue Kanyx-Verzeichnis kopieren.** Der alte Dateiname `data/pyban.db` wird automatisch erkannt und unverändert weiterverwendet. Bei einer neuen Installation entsteht `data/kanyx.db`. Datenbanken **nicht parallel** unter beiden Namen im selben Datenordner betreiben; falls beide existieren, wird `kanyx.db` bevorzugt. Die Anwendung ist nicht für parallele Zugriffe auf denselben USB-Datenträger ausgelegt.

Ablauf: Pyban beenden → Sicherung von `data/` erstellen → Kanyx-Build erstellen → `Kanyx.exe` neben den bestehenden `data/`-Ordner legen → starten. Die alte `Pyban.exe` kann danach entfernt werden. Keine Datenbankumbenennung und keine Neuinstallation erforderlich.

## Icon und Anpassungen

- `assets/kanyx.png`: Anwendungssymbol für Qt-Fenster / Taskleiste
- `assets/kanyx.ico`: Windows-Symbol der EXE
- `ui.py`: Spaltentransparenz im QSS-Eintrag `QFrame#lane` als RGBA-Alpha einstellen (aktuell `225` von `255`).

## Tests

```bash
python -m unittest discover -s tests -v
```

Die grafische Bedienung und Builds müssen auf dem jeweiligen Betriebssystem überprüft werden. Die Veröffentlichung unter einer Open-Source-Lizenz setzt eine bewusste Lizenzwahl voraus; dem Paket ist noch keine Lizenzdatei beigelegt.

## Languages / Sprachen (v0.5)

**English is the default** for new installations. Use the **Language** selector in the toolbar to switch between English, Deutsch, Español, Français, 日本語 and 한국어. The interface switches immediately and the selected language is stored in the existing `data/kanyx.db` (or legacy `data/pyban.db`) in the `settings` table. No internet connection or external translation service is needed. All translations ship with the application in `i18n.py`.

Board titles, column names, card descriptions, tags, checklist content and attachment filenames are **user data and are never translated automatically**. Existing German boards remain unchanged. Priority display strings are translated while the established database values stay compatible. New installations start with an English **My board** title, and new boards get default columns **To Do**, **In Progress**, **Done**.

When updating from v0.4, keep your entire `data/` directory. No database migration or renaming is required. For non-Latin scripts use a system with Japanese/Korean fonts installed; Qt uses the system font fallback.

## v0.6 – Task management (preview source release)

- Archive cards from the task editor and restore them via the Archive toolbar button. Archived cards are excluded from board search.
- Duplicate cards, including independent copies of attachment files, tags, and checklist; duplicate boards from Manage Board.
- Collapse or expand columns with the arrow in the column header; collapse states persist in SQLite.
- Session-scoped Undo / Redo for card drag-and-drop, column movement / renaming, board renaming, archiving, and duplication. **Not all actions are undoable yet** (e.g. permanent deletes, attachment edits or changes inside the task editor).
- Keyboard shortcuts: `Ctrl+Z` undo, `Ctrl+Shift+Z` or `Ctrl+Y` redo, `Ctrl+F` search, `Ctrl+N` add a column.
- New strings translated for all six bundled interface languages.

### Update from v0.5

Close Kanyx, and make a copy of the complete `data/` directory before updating. Replace source files with v0.6 and run `scripts/build_windows.bat` to build the Windows executable; preserve `data/` next to the executable. The migration adds `cards.archived_at` and `lanes.collapsed`, creates a pre-migration database backup in `data/backups/`, and does not rename your old database. The application has not yet been GUI-tested on Windows or Linux in this environment.

## v0.7.1 – UI fixes

- Checklist item editing: explicitly styled inline text editor with legible foreground, background and selection on Windows dark mode. Double-click an item to rename it.
- Card dragging: translucent (68% opacity) snapshot of the actual task card follows the pointer while dragging it between columns or within a column. No additional dependencies.
- No changes to the database format or storage paths. Retain the existing `data/` directory when updating.

## Neu in v0.7.1

- **Markdown:** Im Karteneditor „Markdown preview“ anklicken, um zwischen Rohtext und Vorschau umzuschalten. Die Beschreibung bleibt editierbarer Markdown-Text; der Editor speichert keine HTML-Transformation.
- **Kartenfarben:** Pro Karte ist ein optionaler Akzentstreifen wählbar; Farben werden beim Duplizieren mitkopiert.
- **Checklisten:** Auf der Karte erscheint zusätzlich zum Zähler ein Fortschrittsbalken.
- **Vorlagen:** Über „Templates“ ein Board mit vordefinierten Spalten erzeugen; die Spalten sind danach gewöhnlich editierbar.
- **Kürzel:** Ctrl+N (Spalte), Ctrl+Shift+N (Board), Ctrl+F bzw. Ctrl+L (Suche), Escape (Filter zurücksetzen), Ctrl+1/2/3 (Board 1–3), Ctrl+Z (Undo), Ctrl+Y/Ctrl+Shift+Z (Redo).
- **Migration:** Die Spalte `cards.color` wird automatisch angelegt. Vor der Änderung wird ein `before_v07_*.db`-Backup erzeugt. Vor einem Update den gesamten `data/`-Ordner zusätzlich selbst sichern.

### Testen

Im Projektverzeichnis: `python -m unittest discover -s tests -v`. Für visuelle Funktionen ist weiterhin ein Test auf dem Windows- bzw. Linux-Desktop erforderlich.

## v0.7.1 – Corrections

- Markdown source (including HTML tags such as `<b>Test</b>`) remains verbatim in the editor and database; preview never replaces the editable source.
- Markdown preview toggle now has a visibly highlighted active state.
- Card colors show swatches and tinted entries in their selection menu.

## v0.7.2 – Markdown-Vorschau beim Öffnen

- Bereits bestehende Karten öffnen im aktiven Markdown-Vorschaumodus. Der Button ist sichtbar aktiviert.
- Neu angelegte Karten öffnen im editierbaren Quelltextmodus.
- Beim Zurückschalten in den Bearbeitungsmodus bleibt der ursprüngliche Markdown-/HTML-Quelltext unverändert.


## v0.8: Portable Workspaces und Datensicherheit

Oben in der Werkzeugleiste befindet sich das Menü **Workspace**:

- **Export workspace…**: Speichert das gesamte aktuelle Projekt (alle Boards, Karten, Einstellungen, Anhänge, Wallpaper) in **eine einzige `.kanyx`-Datei**. Eine konsistente SQLite-Sicherung wird während des Exports angefertigt.
- **Import workspace…**: Öffnet ein zuvor exportiertes Workspace-Archiv. **Achtung: Der Import ersetzt den gesamten aktuellen Workspace, er fügt nicht einzelne Boards hinzu.** Vor dem Austausch werden Archivstruktur, SHA-256-Prüfsummen, Datenbankintegrität und referenzierte Anhänge geprüft. Der vorhandene `data`-Ordner wird in einen Ordner `.kanyx-previous-...` direkt neben `data` verschoben und **nicht automatisch gelöscht**. So kann der vorherige Zustand bei Bedarf manuell wiederhergestellt werden.
- **Create database backup**: Erstellt eine zusätzliche SQLite-Sicherung in `data/backups/manual_....db`. Diese enthält nur die Datenbank, **nicht die Anhänge**. Für eine vollständige Sicherung unbedingt `.kanyx` exportieren.
- **Check data integrity**: Prüft die SQLite-Datenbank auf Konsistenz und meldet fehlende Dateianhänge beziehungsweise Wallpaper.

Der `.kanyx`-Container ist ein ZIP-Archiv mit `manifest.json`, `workspace.db` sowie `attachments/` und `wallpapers/`. Das Manifest enthält SHA-256-Prüfsummen und Dateigrößen. Der Import akzeptiert nur das aktuelle Format (Version 1). ZIP-Pfadmanipulation und Dateiübergrößen werden abgewiesen. Import und Export sind vollständig offline.

Automatische tägliche DB-Sicherungen bleiben erhalten. Nur die täglichen Sicherungen unter `data/backups/YYYY-MM-DD.db` werden auf 14 Versionen begrenzt; Vor-Migrationssicherungen und manuelle Backups werden davon nicht erfasst. Das verhindert einen automatischen Verlust dieser Sicherungen, bedeutet aber auch, dass Benutzer den Speicherplatz bei Bedarf selbst kontrollieren sollten.

## Aktualisierung von v0.7.2

1. Kanyx beenden und den bisherigen `data/`-Ordner vollständig sichern.
2. Aktuellen Quellcode entpacken und **den bestehenden `data/`-Ordner beibehalten**.
3. Unter Windows `scripts\build_windows.bat` ausführen oder `python main.py` starten.
4. Im neuen Menü **Workspace** einen vollständigen `.kanyx`-Export erstellen und optional die Integritätsprüfung durchführen.

**Grenzen der v0.8:** Import ersetzt einen Workspace vollständig, keine Board-Zusammenführung. Parallelzugriff auf dieselbe portable Datenbank von mehreren gestarteten Programmen ist nicht vorgesehen. Linux muss separat auf einem kompatiblen Linux-System gebaut werden. Die Qt-Oberfläche sowie Builds müssen auf realen Zielsystemen praktisch getestet werden.

## Darstellung (v0.9)

Oben auf **Appearance** klicken. Die Regler steuern Hintergrundhelligkeit (0–100 %), Spaltendeckkraft (45–100 %) und Textskalierung (80–140 %). Änderungen werden sofort angezeigt, aber erst mit **OK** in der Workspace-Datenbank gespeichert. **Cancel** verwirft sie. **Restore Defaults** setzt auf 39 %, 88 % und 100 % zurück. Bei der Skalierung werden Textgrößen angepasst; Betriebssystem-DPI und native Fensterdekoration werden nicht verändert. Die Einstellung gilt für den Workspace auf dem USB-Stick.

Keine Mehrinstanz-Sperre vorgesehen: Eine USB-Datenbank soll nicht auf mehreren Rechnern zeitgleich verwendet werden.
