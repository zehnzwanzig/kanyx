"""Kanyx portable workspace archives (.kanyx). Pure Python; no Qt dependency.

Format: ZIP with manifest.json, workspace.db, attachments/*, wallpapers/*.
Exports are SQLite-consistent snapshots. Imports validate before replacing data.
"""
import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

FORMAT = 'kanyx-workspace'
FORMAT_VERSION = 1
MAX_FILES = 10000
MAX_UNCOMPRESSED = 2 * 1024**3
MAX_SINGLE_FILE = 512 * 1024**2


def _sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def _db_check(dbpath):
    con = sqlite3.connect(f'file:{dbpath.as_posix()}?mode=ro', uri=True)
    try:
        results = [r[0] for r in con.execute('PRAGMA integrity_check').fetchall()]
        if results != ['ok']:
            raise ValueError('SQLite integrity check failed: ' + '; '.join(results[:5]))
        if con.execute('PRAGMA foreign_key_check').fetchone():
            raise ValueError('SQLite foreign key validation failed')
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {'boards', 'lanes', 'cards', 'settings', 'files', 'checklist', 'card_tags', 'tags'} <= tables:
            raise ValueError('Not a Kanyx database')
        for name in ('files','boards','lanes','cards'):
            con.execute('SELECT * FROM ' + name + ' LIMIT 1').fetchall()
    finally:
        con.close()


def export_workspace(store, destination):
    """Export database and linked data as a verified, fully offline archive."""
    destination = Path(destination).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.suffix.lower() != '.kanyx':
        destination = destination.with_suffix('.kanyx')
    with tempfile.TemporaryDirectory(prefix='.kanyx-export-', dir=store.root) as temp:
        temp = Path(temp)
        snapshot = temp / 'workspace.db'
        db = sqlite3.connect(snapshot)
        try:
            store.con.backup(db)
        finally:
            db.close()
        _db_check(snapshot)
        files = {'workspace.db': snapshot}
        for folder in ('attachments', 'wallpapers'):
            directory = store.data / folder
            if directory.is_dir():
                for entry in directory.iterdir():
                    if entry.is_symlink():
                        raise ValueError('Symlinks are not supported in workspace attachments')
                    if entry.is_file():
                        files[f'{folder}/{entry.name}'] = entry
        # Verify that every attachment in SQLite is actually available.
        for row in store.rows('SELECT stored_name FROM files'):
            name = row['stored_name']
            if not name or Path(name).name != name or f'attachments/{name}' not in files:
                raise ValueError('Missing or unsafe attachment: ' + str(name))
        wp = store.setting('wallpaper')
        if wp and (Path(wp).name != wp or f'wallpapers/{wp}' not in files):
            raise ValueError('Missing wallpaper: ' + str(wp))
        metadata = {'format': FORMAT, 'version': FORMAT_VERSION,
            'created_utc': datetime.now(timezone.utc).isoformat(),
            'files': {name: {'size': path.stat().st_size, 'sha256': _sha256(path)}
                      for name,path in sorted(files.items())}}
        temporary_archive = destination.with_name('.' + uuid.uuid4().hex + '.tmp')
        try:
            with zipfile.ZipFile(temporary_archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as z:
                z.writestr('manifest.json', json.dumps(metadata, indent=2, ensure_ascii=False))
                for name,path in files.items():
                    z.write(path, name)
            os.replace(temporary_archive, destination)
        finally:
            temporary_archive.unlink(missing_ok=True)
    return destination


def _validate_archive(archive):
    with zipfile.ZipFile(archive) as z:
        entries = z.infolist()
        if len(entries) > MAX_FILES or sum(i.file_size for i in entries) > MAX_UNCOMPRESSED:
            raise ValueError('Archive is too large')
        if any(i.file_size > MAX_SINGLE_FILE for i in entries):
            raise ValueError('An archive entry is too large')
        names = [i.filename for i in entries]
        if len(names) != len(set(names)):
            raise ValueError('Duplicate archive entries')
        for info in entries:
            path = PurePosixPath(info.filename)
            if path.is_absolute() or '..' in path.parts or '\\' in info.filename or not path.parts or info.is_dir():
                raise ValueError('Unsafe archive path')
            if info.external_attr >> 16 & 0o170000 == 0o120000:
                raise ValueError('Archive contains a symlink')
        if 'manifest.json' not in names:
            raise ValueError('Missing manifest')
        if z.getinfo('manifest.json').file_size > 1024*1024:
            raise ValueError('Manifest too large')
        manifest = json.loads(z.read('manifest.json'))
        if manifest.get('format') != FORMAT or manifest.get('version') != FORMAT_VERSION:
            raise ValueError('Unsupported .kanyx format version')
        expected = manifest.get('files')
        if not isinstance(expected, dict) or 'workspace.db' not in expected:
            raise ValueError('Incomplete manifest')
        if set(names) != set(expected) | {'manifest.json'}:
            raise ValueError('Archive contents do not match manifest')
        for name, properties in expected.items():
            parts = PurePosixPath(name).parts
            if not (name == 'workspace.db' or
                (len(parts) == 2 and parts[0] in ('attachments','wallpapers') and parts[1] not in ('.','..'))):
                raise ValueError('Unexpected archive file: ' + name)
            if z.getinfo(name).file_size != properties.get('size'):
                raise ValueError('Archive file size mismatch: ' + name)
        return manifest


def stage_import(archive, root):
    """Validate and extract a workspace into a temporary data folder.
    The existing workspace is untouched until caller invokes swap_in_workspace.
    """
    archive = Path(archive)
    root = Path(root)
    manifest = _validate_archive(archive)
    stage = Path(tempfile.mkdtemp(prefix='.kanyx-import-', dir=root))
    target = stage / 'data'
    target.mkdir()
    try:
        with zipfile.ZipFile(archive) as z:
            for name, properties in manifest['files'].items():
                dest = target / ('kanyx.db' if name == 'workspace.db' else name)
                dest.parent.mkdir(parents=True, exist_ok=True)
                hasher = hashlib.sha256()
                with z.open(name) as source, open(dest, 'wb') as output:
                    while True:
                        chunk = source.read(1024*1024)
                        if not chunk: break
                        hasher.update(chunk)
                        output.write(chunk)
                if hasher.hexdigest() != properties.get('sha256'):
                    raise ValueError('Archive checksum mismatch: ' + name)
        _db_check(target / 'kanyx.db')
        con = sqlite3.connect(target / 'kanyx.db')
        try:
            for (name,) in con.execute('SELECT stored_name FROM files'):
                if not name or Path(name).name != name or not (target / 'attachments' / name).is_file():
                    raise ValueError('Missing attachment in imported workspace: ' + str(name))
            row = con.execute("SELECT value FROM settings WHERE key='wallpaper'").fetchone()
            if row and row[0] and (Path(row[0]).name != row[0] or not (target / 'wallpapers' / row[0]).is_file()):
                raise ValueError('Missing wallpaper in imported workspace')
        finally:
            con.close()
        for folder in ('attachments','wallpapers','backups'):
            (target / folder).mkdir(exist_ok=True)
        return stage
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def swap_in_workspace(store, staged):
    """Replace active workspace after verification. A local rollback folder is retained
    if the swap cannot complete. Returns the path of the previous data directory.
    """
    staged = Path(staged)
    incoming = staged / 'data'
    _db_check(incoming / 'kanyx.db')
    old_data = store.data
    rollback = store.root / ('.kanyx-previous-' + datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    store.con.close()
    old_moved = False
    try:
        os.replace(old_data, rollback)
        old_moved = True
        os.replace(incoming, old_data)
        store.dbfile = old_data / 'kanyx.db'
        store.con = sqlite3.connect(store.dbfile)
        store.con.row_factory = sqlite3.Row
        store.con.execute('PRAGMA foreign_keys=ON')
        store.con.execute('PRAGMA busy_timeout=5000')
        _db_check(store.dbfile)
        return rollback
    except Exception:
        if old_moved:
            if old_data.exists():
                shutil.rmtree(old_data)
            os.replace(rollback, old_data)
        store.dbfile = old_data / ('pyban.db' if (old_data / 'pyban.db').exists() and not (old_data / 'kanyx.db').exists() else 'kanyx.db')
        store.con = sqlite3.connect(store.dbfile)
        store.con.row_factory = sqlite3.Row
        store.con.execute('PRAGMA foreign_keys=ON')
        store.con.execute('PRAGMA busy_timeout=5000')
        raise
    finally:
        shutil.rmtree(staged, ignore_errors=True)
