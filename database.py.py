import sqlite3
from typing import Optional

class Database:
    def __init__(self, db_path: str = "parti.db"):
        self.db_path = db_path
        self._init_db()
    def _baglanti(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    def _init_db(self):
        with self._baglanti() as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS kullanicilar (user_id INTEGER PRIMARY KEY, username TEXT, xp INTEGER DEFAULT 0, level INTEGER DEFAULT 1, guven INTEGER DEFAULT 100, streak INTEGER DEFAULT 0, last_task TEXT, role TEXT, created_at TEXT DEFAULT (date('now')))")
    def kullanici_ekle(self, user_id, username):
        with self._baglanti() as conn:
            conn.execute("INSERT OR IGNORE INTO kullanicilar (user_id, username) VALUES (?,?)", (user_id, username))
    def kullanici_getir(self, user_id):
        with self._baglanti() as conn:
            r = conn.execute("SELECT * FROM kullanicilar WHERE user_id=?", (user_id,)).fetchone()
            return dict(r) if r else None
    def kullanici_username_ile_getir(self, username):
        with self._baglanti() as conn:
            r = conn.execute("SELECT * FROM kullanicilar WHERE LOWER(username)=LOWER(?)", (username,)).fetchone()
            return dict(r) if r else None
    def kullanici_guncelle(self, user_id, **kwargs):
        if not kwargs: return
        cols = ", ".join(f"{k}=?" for k in kwargs)
        vals = list(kwargs.values()) + [user_id]
        with self._baglanti() as conn:
            conn.execute(f"UPDATE kullanicilar SET {cols} WHERE user_id=?", vals)
    def rol_ata(self, user_id, rol):
        with self._baglanti() as conn:
            conn.execute("UPDATE kullanicilar SET role=? WHERE user_id=?", (rol, user_id))
    def lider_tablosu(self):
        with self._baglanti() as conn:
            rows = conn.execute("SELECT username, xp, role, guven FROM kullanicilar ORDER BY xp DESC LIMIT 10").fetchall()
            return [(r["username"], r["xp"], r["role"], r["guven"]) for r in rows]
    def tum_kullanicilari_getir(self):
        with self._baglanti() as conn:
            rows = conn.execute("SELECT user_id, username FROM kullanicilar").fetchall()
            return [(r["user_id"], r["username"]) for r in rows]