"""Data operations for Kanyx swimlanes/calendar; no Qt dependency.

Run migrate_swimlanes on Store startup and after importing an older workspace.
It is idempotent and preserves existing board/card IDs and attachment references.
"""
import sqlite3
from datetime import date


def migrate_swimlanes(store):
    con = store.con
    # One complete backup before the first schema change, not on every launch.
    columns = {r['name'] for r in store.rows('PRAGMA table_info(cards)')}
    if 'swimlane_id' not in columns:
        from datetime import datetime
        backup = store.backups / ('before_swimlanes_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.db')
        snapshot = sqlite3.connect(backup)
        try:
            con.backup(snapshot)
        finally:
            snapshot.close()
    with con:
        con.execute('''CREATE TABLE IF NOT EXISTS swimlanes (
            id INTEGER PRIMARY KEY,
            board_id INTEGER NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            position INTEGER NOT NULL DEFAULT 0,
            collapsed INTEGER NOT NULL DEFAULT 0,
            is_default INTEGER NOT NULL DEFAULT 0)''')
        if 'swimlane_id' not in columns:
            con.execute('ALTER TABLE cards ADD COLUMN swimlane_id INTEGER REFERENCES swimlanes(id) ON DELETE SET NULL')
        for row in store.rows('SELECT id FROM boards'):
            board_id = row['id']
            row_default = store.one('SELECT id FROM swimlanes WHERE board_id=? AND is_default=1 ORDER BY id LIMIT 1', (board_id,))
            if row_default is None:
                # Existing cards must be assigned to the first lane on migration.
                lane_id = con.execute('INSERT INTO swimlanes(board_id,title,position,is_default) VALUES(?,?,0,1)',
                                     (board_id, 'General')).lastrowid
            else:
                lane_id = row_default['id']
            con.execute('''UPDATE cards SET swimlane_id=? WHERE swimlane_id IS NULL
                       AND lane_id IN (SELECT id FROM lanes WHERE board_id=?)''', (lane_id,board_id))


def swimlanes(store, board_id):
    return store.rows('SELECT * FROM swimlanes WHERE board_id=? ORDER BY position,id', (board_id,))


def default_swimlane(store, board_id):
    row = store.one('SELECT id FROM swimlanes WHERE board_id=? AND is_default=1 ORDER BY id LIMIT 1', (board_id,))
    if row:
        return row['id']
    with store.con:
        result = store.con.execute('INSERT INTO swimlanes(board_id,title,position,is_default) VALUES(?,?,0,1)', (board_id,'General'))
        return result.lastrowid


def add_swimlane(store, board_id, title):
    title = title.strip()
    if not title or len(title) > 150:
        raise ValueError('Swimlane name must have 1–150 characters')
    if not store.one('SELECT id FROM boards WHERE id=?', (board_id,)):
        raise ValueError('Unknown board')
    with store.con:
        return store.con.execute('''INSERT INTO swimlanes(board_id,title,position)
            VALUES(?,?,(SELECT COUNT(*) FROM swimlanes WHERE board_id=?))''', (board_id,title,board_id)).lastrowid


def rename_swimlane(store, sid, title):
    title = title.strip()
    if not title or len(title)>150:
        raise ValueError('Invalid swimlane name')
    with store.con:
        cur=store.con.execute('UPDATE swimlanes SET title=? WHERE id=?',(title,sid))
        if cur.rowcount != 1: raise ValueError('Unknown swimlane')


def set_swimlane_collapsed(store, sid, collapsed):
    with store.con:
        store.con.execute('UPDATE swimlanes SET collapsed=? WHERE id=?', (int(bool(collapsed)),sid))


def move_swimlane(store,sid,position):
    sl = store.one('SELECT board_id FROM swimlanes WHERE id=?',(sid,))
    if not sl: raise ValueError('Unknown swimlane')
    ids=[r['id'] for r in swimlanes(store,sl['board_id']) if r['id'] != sid]
    ids.insert(max(0,min(int(position),len(ids))),sid)
    with store.con:
        for pos,i in enumerate(ids):
            store.con.execute('UPDATE swimlanes SET position=? WHERE id=?',(pos,i))


def delete_swimlane(store,sid):
    sl=store.one('SELECT board_id,is_default FROM swimlanes WHERE id=?',(sid,))
    if not sl: return
    if sl['is_default']:
        raise ValueError('The default swimlane cannot be deleted')
    default=default_swimlane(store,sl['board_id'])
    with store.con:
        store.con.execute('UPDATE cards SET swimlane_id=? WHERE swimlane_id=?',(default,sid))
        store.con.execute('DELETE FROM swimlanes WHERE id=?',(sid,))
        rest=swimlanes(store,sl['board_id'])
        for pos,other in enumerate(rest):
            store.con.execute('UPDATE swimlanes SET position=? WHERE id=?',(pos,other['id']))


def assign_swimlane(store,cid,sid):
    if sid is None:
        return
    card=store.one('''SELECT c.id,l.board_id FROM cards c JOIN lanes l ON l.id=c.lane_id WHERE c.id=?''',(cid,))
    target=store.one('SELECT board_id FROM swimlanes WHERE id=?',(sid,))
    if not card or not target or card['board_id'] != target['board_id']:
        raise ValueError('Swimlane does not belong to the card board')
    with store.con:
        store.con.execute('UPDATE cards SET swimlane_id=? WHERE id=?',(sid,cid))


def move_card_to_swimlane(store,cid, target_lane, index, sid):
    card=store.one('''SELECT c.lane_id,c.swimlane_id,l.board_id AS source_board
        FROM cards c JOIN lanes l ON l.id=c.lane_id WHERE c.id=?''',(cid,))
    lane=store.one('SELECT board_id FROM lanes WHERE id=?',(target_lane,))
    swim=store.one('SELECT board_id FROM swimlanes WHERE id=?',(sid,))
    if not card or not lane or not swim or lane['board_id'] != swim['board_id'] or card['source_board'] != lane['board_id']:
        raise ValueError('Cannot move card to another board')
    source_lane=card['lane_id']
    with store.con:
        store.con.execute('UPDATE cards SET lane_id=?,swimlane_id=? WHERE id=?',(target_lane,sid,cid))
        # Recompute order per swimlane, then flatten by swimlane position.
        rows=store.rows('SELECT id,swimlane_id FROM cards WHERE lane_id=? AND id<>? ORDER BY position,id',(target_lane,cid))
        groups={}
        for row in rows:
            groups.setdefault(row['swimlane_id'],[]).append(row['id'])
        destination=groups.setdefault(sid,[])
        destination.insert(max(0,min(int(index),len(destination))),cid)
        ids=[r['id'] for r in swimlanes(store,lane['board_id'])]
        all_ids=[]
        for group_id in ids:
            all_ids.extend(groups.pop(group_id,[]))
        for remaining in groups.values():
            all_ids.extend(remaining)
        for pos,card_id in enumerate(all_ids):
            store.con.execute('UPDATE cards SET position=? WHERE id=?',(pos,card_id))
        if source_lane != target_lane:
            source=store.rows('SELECT id FROM cards WHERE lane_id=? ORDER BY position,id',(source_lane,))
            for pos,r in enumerate(source):
                store.con.execute('UPDATE cards SET position=? WHERE id=?',(pos,r['id']))


def due_cards(store,board_id=None):
    if board_id is None:
        return store.rows('''SELECT c.id,c.title,c.due,c.priority,c.lane_id,l.board_id,b.title AS board_title
            FROM cards c JOIN lanes l ON l.id=c.lane_id JOIN boards b ON b.id=l.board_id
            WHERE c.archived_at IS NULL AND c.due<>'' ORDER BY c.due,c.position,c.id''')
    return store.rows('''SELECT c.id,c.title,c.due,c.priority,c.lane_id,l.board_id,b.title AS board_title
            FROM cards c JOIN lanes l ON l.id=c.lane_id JOIN boards b ON b.id=l.board_id
            WHERE c.archived_at IS NULL AND c.due<>'' AND l.board_id=?
            ORDER BY c.due,c.position,c.id''',(board_id,))


def set_due(store,cid,day):
    # ISO dates only, prevents inserting invalid calendar values.
    if day:
        day=date.fromisoformat(day).isoformat()
    with store.con:
        r=store.con.execute('UPDATE cards SET due=? WHERE id=?',(day,cid))
        if r.rowcount!=1:
            raise ValueError('Unknown task')
