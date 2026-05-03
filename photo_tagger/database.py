import sqlite3
import os

DB_PATH = "photos.db"

def init_db():
    """Tworzy tabele jeśli nie istnieją. Migruje stary schemat jeśli trzeba."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Migracja: usuń UNIQUE z path jeśli istnieje
    c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='photos'")
    row = c.fetchone()
    if row and "UNIQUE" in row[0].upper():
        c.execute("ALTER TABLE photos RENAME TO photos_old")
        c.execute('''
            CREATE TABLE photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL,
                filename TEXT NOT NULL,
                model_used TEXT DEFAULT 'unknown',
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute("INSERT INTO photos (id, path, filename, added_at) SELECT id, path, filename, added_at FROM photos_old")
        c.execute("DROP TABLE photos_old")
        conn.commit()

    c.execute('''
        CREATE TABLE IF NOT EXISTS photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT NOT NULL,
            filename TEXT NOT NULL,
            model_used TEXT DEFAULT 'unknown',
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            photo_id INTEGER NOT NULL,
            tag TEXT NOT NULL,
            confidence REAL,
            FOREIGN KEY (photo_id) REFERENCES photos(id)
        )
    ''')

    # Migracja: dodaj kolumnę model_used jeśli brakuje
    c.execute("PRAGMA table_info(photos)")
    cols = [r[1] for r in c.fetchall()]
    if "model_used" not in cols:
        c.execute("ALTER TABLE photos ADD COLUMN model_used TEXT DEFAULT 'unknown'")

    conn.commit()
    conn.close()

def add_photo(path, model_used="unknown"):
    """Dodaje zdjęcie do bazy (duplikaty dozwolone), zwraca jego ID"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    filename = os.path.basename(path)
    c.execute('INSERT INTO photos (path, filename, model_used) VALUES (?, ?, ?)',
              (path, filename, model_used))
    conn.commit()
    photo_id = c.lastrowid
    conn.close()
    return photo_id

def add_tags(photo_id, tags):
    """
    Dodaje tagi do zdjęcia.
    tags = lista słowników: [{"tag": "person", "confidence": 0.95}, ...]
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # usuń stare tagi żeby nie duplikować przy ponownym skanowaniu
    c.execute('DELETE FROM tags WHERE photo_id = ?', (photo_id,))
    for t in tags:
        c.execute('INSERT INTO tags (photo_id, tag, confidence) VALUES (?, ?, ?)',
                  (photo_id, t["tag"], t["confidence"]))
    conn.commit()
    conn.close()

def get_all_tags():
    """Zwraca listę unikalnych tagów (do panelu bocznego)"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT DISTINCT tag FROM tags ORDER BY tag')
    tags = [row[0] for row in c.fetchall()]
    conn.close()
    return tags

def get_photos_by_tag(tag):
    """Zwraca ścieżki zdjęć z danym tagiem"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT p.path FROM photos p
        JOIN tags t ON p.id = t.photo_id
        WHERE t.tag = ?
    ''', (tag,))
    paths = [row[0] for row in c.fetchall()]
    conn.close()
    return paths

def get_tags_for_photo(path):
    """Zwraca tagi + model_used dla ostatniego skanu zdjęcia"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Pobierz ostatni wpis dla tej ścieżki
    c.execute('SELECT id, model_used FROM photos WHERE path = ? ORDER BY added_at DESC LIMIT 1', (path,))
    photo_row = c.fetchone()
    if not photo_row:
        conn.close()
        return [], "unknown"
    photo_id, model_used = photo_row
    c.execute('''
        SELECT tag, confidence FROM tags
        WHERE photo_id = ?
        ORDER BY confidence DESC
    ''', (photo_id,))
    tags = [{"tag": row[0], "confidence": row[1]} for row in c.fetchall()]
    conn.close()
    return tags, model_used

def delete_photo(path):
    """Usuwa zdjęcie i jego tagi z bazy (wszystkie wpisy z daną ścieżką)."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id FROM photos WHERE path = ?', (path,))
    ids = [row[0] for row in c.fetchall()]
    for pid in ids:
        c.execute('DELETE FROM tags WHERE photo_id = ?', (pid,))
    c.execute('DELETE FROM photos WHERE path = ?', (path,))
    conn.commit()
    conn.close()


def get_all_photos():
    """Zwraca wszystkie zdjęcia z bazy"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT path FROM photos ORDER BY added_at DESC')
    paths = [row[0] for row in c.fetchall()]
    conn.close()
    return paths

