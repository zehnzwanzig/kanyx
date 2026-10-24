import sqlite3
import os
import sys
import shutil
import uuid
from pathlib import Path
from datetime import datetime


def root_path():
    return Path(sys.executable if getattr(sys, 'frozen', False) else __file__).resolve().parent


class Store:
    def __init__(self, root=None):
        self.root = Path(root) if root else root_path()
        self.data = self.root / 'data'
        self.attachments = self.data / 'attachments'
        self.backups = self.data / 'backups'
        self.wallpapers = self.data / 'wallpapers'
        for folder in (self.data, self.attachments, self.backups, self.wallpapers):
            folder.mkdir(parents=True, exist_ok=True)
        # Bestehende Pyban-Datenbank weiterverwenden; neue Installationen nutzen kanyx.db.
        legacy_db = self.data / 'pyban.db'
        modern_db = self.data / 'kanyx.db'
        self.dbfile = modern_db if modern_db.exists() else (legacy_db if legacy_db.exists() else modern_db)
        self.con = sqlite3.connect(self.dbfile)
        self.con.row_factory = sqlite3.Row
        self.con.execute('PRAGMA foreign_keys=ON')
        self.con.execute('PRAGMA busy_timeout=5000')
        self.con.executescript('''
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS boards (id INTEGER PRIMARY KEY, title TEXT NOT NULL, position INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS lanes (id INTEGER PRIMARY KEY, board_id INTEGER NOT NULL REFERENCES boards(id) ON DELETE CASCADE, title TEXT NOT NULL, position INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS cards (id INTEGER PRIMARY KEY, lane_id INTEGER NOT NULL REFERENCES lanes(id) ON DELETE CASCADE,
          title TEXT NOT NULL, description TEXT NOT NULL DEFAULT '', priority TEXT NOT NULL DEFAULT 'Normal', due TEXT NOT NULL DEFAULT '',
          position INTEGER NOT NULL DEFAULT 0, created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS tags (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE COLLATE NOCASE);
        CREATE TABLE IF NOT EXISTS card_tags (card_id INTEGER NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
          tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE, PRIMARY KEY(card_id,tag_id));
        CREATE TABLE IF NOT EXISTS checklist (id INTEGER PRIMARY KEY, card_id INTEGER NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
          body TEXT NOT NULL, done INTEGER NOT NULL DEFAULT 0, position INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS files (id INTEGER PRIMARY KEY, card_id INTEGER NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
          original_name TEXT NOT NULL, stored_name TEXT NOT NULL);
        ''')
        self.con.commit()
        # Back up older schemas BEFORE altering columns.
        existing_columns = {c['name'] for c in self.rows('PRAGMA table_info(cards)')}
        if 'archived_at' not in existing_columns and self.dbfile.exists():
            backup = self.backups / ('before_v06_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.db')
            destination = sqlite3.connect(backup)
            try:
                self.con.backup(destination)
            finally:
                destination.close()
        # Schema upgrade: preserve all existing cards and attachments.
        columns = {c['name'] for c in self.rows('PRAGMA table_info(cards)')}
        if 'archived_at' not in columns:
            self.execute('ALTER TABLE cards ADD COLUMN archived_at TEXT DEFAULT NULL')
        lane_columns = {c['name'] for c in self.rows('PRAGMA table_info(lanes)')}
        if 'collapsed' not in lane_columns:
            self.execute('ALTER TABLE lanes ADD COLUMN collapsed INTEGER NOT NULL DEFAULT 0')
        # v0.7: optional colour accent; preserve existing card data.
        card_columns = {c['name'] for c in self.rows('PRAGMA table_info(cards)')}
        if 'color' not in card_columns:
            backup = self.backups / ('before_v07_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.db')
            destination = sqlite3.connect(backup)
            try:
                self.con.backup(destination)
            finally:
                destination.close()
            self.execute("ALTER TABLE cards ADD COLUMN color TEXT NOT NULL DEFAULT ''")
        if not self.rows('SELECT id FROM boards LIMIT 1'):
            board = self.add_board('My board')
            for title in ('To Do', 'In Progress', 'Done'):
                self.add_lane(board, title)
        self.backup_if_needed()

    def rows(self, sql, params=()):
        return [dict(r) for r in self.con.execute(sql, params).fetchall()]

    def one(self, sql, params=()):
        r = self.con.execute(sql, params).fetchone()
        return dict(r) if r else None

    def execute(self, sql, params=()):
        with self.con:
            return self.con.execute(sql, params).lastrowid

    def setting(self, key, default=''):
        row = self.one('SELECT value FROM settings WHERE key=?', (key,))
        return row['value'] if row else default

    def set_setting(self, key, value):
        self.execute('INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value', (key, str(value)))

    def set_wallpaper(self, source):
        """Copy the selected image into the portable data directory."""
        source = Path(source)
        if not source.is_file():
            raise FileNotFoundError(source)
        filename = 'wallpaper_' + uuid.uuid4().hex + source.suffix.lower()
        destination = self.wallpapers / filename
        shutil.copy2(source, destination)
        previous = self.setting('wallpaper')
        try:
            self.set_setting('wallpaper', filename)
        except Exception:
            destination.unlink(missing_ok=True)
            raise
        if previous and previous != filename:
            (self.wallpapers / Path(previous).name).unlink(missing_ok=True)
        return destination

    def clear_wallpaper(self):
        previous = self.setting('wallpaper')
        self.set_setting('wallpaper', '')
        if previous:
            (self.wallpapers / Path(previous).name).unlink(missing_ok=True)

    def wallpaper_path(self):
        filename = self.setting('wallpaper')
        return self.wallpapers / Path(filename).name if filename else None

    def move_lane(self, lane_id, new_position):
        """Move a lane to an absolute zero-based position on its existing board."""
        lane = self.one('SELECT id,board_id FROM lanes WHERE id=?', (lane_id,))
        if not lane:
            return
        ids = [r['id'] for r in self.rows('SELECT id FROM lanes WHERE board_id=? ORDER BY position,id', (lane['board_id'],))]
        ids.remove(lane_id)
        ids.insert(max(0, min(int(new_position), len(ids))), lane_id)
        with self.con:
            for index, lid in enumerate(ids):
                self.con.execute('UPDATE lanes SET position=? WHERE id=?', (index, lid))

    def set_lane_collapsed(self, lane_id, collapsed):
        self.execute('UPDATE lanes SET collapsed=? WHERE id=?', (int(collapsed), lane_id))

    def archive_card(self, cid, archive=True):
        self.execute("UPDATE cards SET archived_at=CASE WHEN ? THEN CURRENT_TIMESTAMP ELSE NULL END WHERE id=?", (int(archive), cid))

    def archived_cards(self, board_id):
        return self.rows('''SELECT c.*, l.title AS lane_title FROM cards c
            JOIN lanes l ON l.id=c.lane_id WHERE l.board_id=?
            AND c.archived_at IS NOT NULL ORDER BY c.archived_at DESC, c.id DESC''', (board_id,))

    def duplicate_card(self, cid, target_lane=None):
        original = self.card(cid)
        if not original: raise ValueError('Card not found')
        lane_id = target_lane or original['lane_id']
        with self.con:
            copied = self.con.execute('''INSERT INTO cards(lane_id,title,description,priority,due,position,created,archived_at,color)
                VALUES(?,?,?,?,?,(SELECT COUNT(*) FROM cards WHERE lane_id=?),CURRENT_TIMESTAMP,NULL,?)''',
                (lane_id, original['title']+' (Copy)',original['description'],original['priority'],original['due'],lane_id,original.get('color',''))).lastrowid
            self.con.execute('INSERT INTO card_tags(card_id,tag_id) SELECT ?,tag_id FROM card_tags WHERE card_id=?',(copied,cid))
            self.con.execute('INSERT INTO checklist(card_id,body,done,position) SELECT ?,body,done,position FROM checklist WHERE card_id=?',(copied,cid))
            # Give the duplicate its own attachment files, so deletion remains independent.
            files = self.card_files(cid)
            for f in files:
                src = self.attachments / f['stored_name']
                if src.exists():
                    unique = uuid.uuid4().hex + src.suffix
                    shutil.copy2(src, self.attachments / unique)
                    self.con.execute('INSERT INTO files(card_id,original_name,stored_name) VALUES(?,?,?)',(copied,f['original_name'],unique))
        return copied

    def duplicate_board(self, bid):
        board = self.one('SELECT * FROM boards WHERE id=?',(bid,))
        if not board: raise ValueError('Board not found')
        new_bid = self.add_board(board['title']+' (Copy)')
        for lane in self.rows('SELECT * FROM lanes WHERE board_id=? ORDER BY position,id',(bid,)):
            new_lane = self.add_lane(new_bid,lane['title'])
            self.set_lane_collapsed(new_lane, lane['collapsed'])
            for card in self.rows('SELECT id FROM cards WHERE lane_id=? AND archived_at IS NULL ORDER BY position,id',(lane['id'],)):
                self.duplicate_card(card['id'],new_lane)
        return new_bid

    def create_board_from_template(self, title, template='simple'):
        """Create a conventional editable board from a bundled preset."""
        presets = {
            'simple': ('To Do', 'In Progress', 'Done'),
            'project': ('Ideas', 'To Do', 'In Progress', 'Review', 'Done'),
            'personal': ('Inbox', 'This week', 'Doing', 'Done'),
            'blank': (),
        }
        if template not in presets:
            raise ValueError('Unknown template')
        with self.con:
            bid = self.add_board(title)
            for lane in presets[template]:
                self.add_lane(bid, lane)
        return bid

    def rename_lane(self, lid, title):
        self.execute('UPDATE lanes SET title=? WHERE id=?',(title,lid))

    def rename_board(self, bid, title):
        self.execute('UPDATE boards SET title=? WHERE id=?',(title,bid))

    def add_board(self, title):
        return self.execute('INSERT INTO boards(title,position) VALUES(?,(SELECT COUNT(*) FROM boards))', (title,))

    def add_lane(self, board_id, title):
        return self.execute('INSERT INTO lanes(board_id,title,position) VALUES(?,?,(SELECT COUNT(*) FROM lanes WHERE board_id=?))', (board_id,title,board_id))

    def add_card(self, lane_id, title):
        return self.execute('INSERT INTO cards(lane_id,title,position) VALUES(?,?,(SELECT COUNT(*) FROM cards WHERE lane_id=?))', (lane_id,title,lane_id))

    def _apply_card_fields(self, cid, title, description, priority, due, tags, checklist, color=None):
        self.con.execute('UPDATE cards SET title=?,description=?,priority=?,due=? WHERE id=?', (title,description,priority,due,cid))
        if color is not None:
            if color not in ('', '#4f98c8', '#6bb6a4', '#d7a15a', '#c97893', '#9a8dd2'):
                raise ValueError('Invalid card accent')
            self.con.execute('UPDATE cards SET color=? WHERE id=?', (color,cid))
        self.con.execute('DELETE FROM card_tags WHERE card_id=?', (cid,))
        for name in sorted({s.strip() for s in tags.split(',') if s.strip()}):
            self.con.execute('INSERT OR IGNORE INTO tags(name) VALUES(?)', (name,))
            tag_id = self.con.execute('SELECT id FROM tags WHERE name=? COLLATE NOCASE',(name,)).fetchone()[0]
            self.con.execute('INSERT OR IGNORE INTO card_tags(card_id,tag_id) VALUES(?,?)', (cid,tag_id))
        self.con.execute('DELETE FROM checklist WHERE card_id=?', (cid,))
        for pos, (body, done) in enumerate(checklist):
            if body.strip():
                self.con.execute('INSERT INTO checklist(card_id,body,done,position) VALUES(?,?,?,?)', (cid,body.strip(),int(done),pos))

    def update_card(self, cid, title, description, priority, due, tags, checklist, color=None):
        with self.con:
            self._apply_card_fields(cid, title, description, priority, due, tags, checklist, color)

    def card(self, cid):
        return self.one('SELECT * FROM cards WHERE id=?',(cid,))

    def card_tags(self, cid):
        return [r['name'] for r in self.rows('SELECT t.name FROM tags t JOIN card_tags ct ON t.id=ct.tag_id WHERE ct.card_id=? ORDER BY t.name',(cid,))]

    def card_checks(self, cid):
        return self.rows('SELECT body,done FROM checklist WHERE card_id=? ORDER BY position,id',(cid,))

    def card_files(self, cid):
        return self.rows('SELECT * FROM files WHERE card_id=? ORDER BY id',(cid,))

    def _attachment_path(self, stored_name):
        """Return a safe path or None. Never follow forged DB paths or symlinks."""
        if (not isinstance(stored_name, str) or not stored_name
                or stored_name in ('.', '..') or '/' in stored_name
                or '\\' in stored_name or '\x00' in stored_name):
            return None
        if self.attachments.is_symlink():
            return None
        path = self.attachments / stored_name
        if path.is_symlink() or path.resolve(strict=False).parent != self.attachments.resolve():
            return None
        return path

    def _stage_removals(self, rows):
        """Move attachments aside so a failed SQL operation can restore them."""
        moved = []
        try:
            for row in rows:
                path = self._attachment_path(row['stored_name'])
                # Bad database paths: forget the DB reference, NEVER touch any other file.
                if path is None or not path.exists():
                    continue
                if not path.is_file():
                    raise OSError('Attachment is not a regular file: ' + str(path))
                trash = self.attachments / ('.kanyx-trash-' + uuid.uuid4().hex)
                os.replace(path, trash)
                moved.append((trash, path))
        except Exception:
            self._restore_removals(moved)
            raise
        return moved

    @staticmethod
    def _restore_removals(moved):
        for trash, original in reversed(moved):
            if trash.exists():
                os.replace(trash, original)

    @staticmethod
    def _finish_removals(moved):
        # Failure to clean a trash file must not undo a committed database edit.
        for trash, _ in moved:
            try:
                trash.unlink(missing_ok=True)
            except OSError:
                pass

    def add_file(self, cid, path):
        src = Path(path)
        unique = f'{uuid.uuid4().hex}{src.suffix.lower()}'
        destination = self.attachments / unique
        try:
            shutil.copy2(src, destination)
            return self.execute('INSERT INTO files(card_id,original_name,stored_name) VALUES(?,?,?)',
                                (cid, src.name, unique))
        except Exception:
            destination.unlink(missing_ok=True)
            raise

    def save_card_with_files(self, cid, title, description, priority, due, tags,
                             checklist, color=None, *, is_new=False, lane_id=None,
                             added_paths=(), removed_ids=()):
        """Commit the card and attachment references together, or leave all unchanged.

        Copies are staged before SQL; removals are reversible until SQL commits.
        This is a best-effort filesystem/SQLite transaction (not crash-atomic).
        """
        added = []
        moved = []
        try:
            for source in added_paths:
                src = Path(source)
                unique = f'{uuid.uuid4().hex}{src.suffix.lower()}'
                destination = self.attachments / unique
                # Register BEFORE copy2: clean up even an interrupted partial copy.
                added.append((src.name, unique, destination))
                shutil.copy2(src, destination)

            remove_ids = list(dict.fromkeys(removed_ids))
            to_remove = []
            if remove_ids:
                if is_new:
                    raise ValueError('Cannot remove attachments from an unsaved card')
                for fid in remove_ids:
                    row = self.one('SELECT id,card_id,stored_name FROM files WHERE id=?', (fid,))
                    if row is None or row['card_id'] != cid:
                        raise ValueError('Attachment does not belong to this card')
                    to_remove.append(row)
            moved = self._stage_removals(to_remove)
            with self.con:
                if is_new:
                    if lane_id is None:
                        raise ValueError('New task requires a target column')
                    cid = self.con.execute(
                        'INSERT INTO cards(lane_id,title,position) VALUES(?,?,(SELECT COUNT(*) FROM cards WHERE lane_id=?))',
                        (lane_id, title, lane_id)).lastrowid
                self._apply_card_fields(cid, title, description, priority, due, tags, checklist, color)
                for original_name, unique, _ in added:
                    self.con.execute('INSERT INTO files(card_id,original_name,stored_name) VALUES(?,?,?)',
                                     (cid, original_name, unique))
                for row in to_remove:
                    self.con.execute('DELETE FROM files WHERE id=?', (row['id'],))
        except Exception:
            self._restore_removals(moved)
            for _, _, path in added:
                path.unlink(missing_ok=True)
            raise
        self._finish_removals(moved)
        return cid

    def delete_file(self, fid):
        row = self.one('SELECT id,stored_name FROM files WHERE id=?', (fid,))
        if row is None:
            return
        moved = self._stage_removals([row])
        try:
            with self.con:
                self.con.execute('DELETE FROM files WHERE id=?', (fid,))
        except Exception:
            self._restore_removals(moved)
            raise
        self._finish_removals(moved)

    def delete_card(self, cid, delete_attachments=True):
        """When False: delete card + file DB references, keep files as orphans."""
        files = self.card_files(cid)
        moved = self._stage_removals(files) if delete_attachments else []
        try:
            with self.con:
                self.con.execute('DELETE FROM cards WHERE id=?', (cid,))
        except Exception:
            self._restore_removals(moved)
            raise
        self._finish_removals(moved)

    def delete_lane(self, lid):
        for r in self.rows('SELECT id FROM cards WHERE lane_id=?',(lid,)):
            self.delete_card(r['id'])
        self.execute('DELETE FROM lanes WHERE id=?',(lid,))

    def delete_board(self, bid):
        for r in self.rows('SELECT id FROM lanes WHERE board_id=?',(bid,)):
            self.delete_lane(r['id'])
        self.execute('DELETE FROM boards WHERE id=?',(bid,))

    def move_card(self, cid, target_lane, target_position):
        source = self.card(cid)
        if not source:
            return
        with self.con:
            self.con.execute('UPDATE cards SET lane_id=? WHERE id=?',(target_lane,cid))
            for lane in set((source['lane_id'],target_lane)):
                ids = [r['id'] for r in self.rows('SELECT id FROM cards WHERE lane_id=? AND id<>? ORDER BY position,id',(lane,cid))]
                if lane == target_lane:
                    ids.insert(max(0,min(target_position,len(ids))),cid)
                for index, card_id in enumerate(ids):
                    self.con.execute('UPDATE cards SET position=? WHERE id=?',(index,card_id))

    def search_cards(self, board_id, term='', priority='Alle'):
        clauses = ['l.board_id=?', 'c.archived_at IS NULL']
        args = [board_id]
        if term:
            clauses.append('''(c.title LIKE ? ESCAPE '!' OR c.description LIKE ? ESCAPE '!' OR EXISTS
            (SELECT 1 FROM card_tags ct JOIN tags t ON t.id=ct.tag_id WHERE ct.card_id=c.id AND t.name LIKE ? ESCAPE '!'))''')
            # Interpret search terms literally, not as SQL LIKE wildcards.
            escaped = term.replace('!', '!!').replace('%', '!%').replace('_', '!_')
            args.extend([f'%{escaped}%']*3)
        if priority != 'Alle':
            clauses.append('c.priority=?')
            args.append(priority)
        return self.rows('SELECT c.* FROM cards c JOIN lanes l ON l.id=c.lane_id WHERE '+' AND '.join(clauses)+' ORDER BY c.position,c.id',args)

    def verify_integrity(self):
        from portability import _db_check
        _db_check(self.dbfile)
        missing = []
        for row in self.rows('SELECT stored_name FROM files'):
            name = row['stored_name']
            if not name or Path(name).name != name or not (self.attachments / name).is_file():
                missing.append(str(name))
        wallpaper = self.setting('wallpaper')
        if wallpaper and (Path(wallpaper).name != wallpaper or not (self.wallpapers / wallpaper).is_file()):
            missing.append('wallpaper: ' + wallpaper)
        return missing

    def backup_now(self):
        from datetime import datetime
        self.verify_integrity_sqlite()
        target = self.backups / ('manual_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.db')
        destination = sqlite3.connect(target)
        try:
            self.con.backup(destination)
        finally:
            destination.close()
        return target

    def verify_integrity_sqlite(self):
        integrity = [r[0] for r in self.con.execute('PRAGMA integrity_check').fetchall()]
        if integrity != ['ok'] or self.con.execute('PRAGMA foreign_key_check').fetchone():
            raise ValueError('Database integrity check failed')

    def backup_if_needed(self):
        target = self.backups / (datetime.now().strftime('%Y-%m-%d')+'.db')
        if not target.exists():
            destination = sqlite3.connect(target)
            try:
                self.con.backup(destination)
            finally:
                destination.close()
        backups = sorted(self.backups.glob('????-??-??.db'))
        for old in backups[:-14]:
            old.unlink()

    def close(self):
        self.con.close()
