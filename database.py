import sqlite3
from config import DB_NAME

class DatabaseManager:
    def __init__(self):
        self.conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.init_db()

    def init_db(self):
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS group_settings (
            chat_id INTEGER PRIMARY KEY,
            welcome INTEGER DEFAULT 1, goodbye INTEGER DEFAULT 1,
            antispam INTEGER DEFAULT 1, antiflood INTEGER DEFAULT 1,
            captcha INTEGER DEFAULT 0, porn INTEGER DEFAULT 1,
            night INTEGER DEFAULT 0, links INTEGER DEFAULT 0,
            stickers INTEGER DEFAULT 0, media INTEGER DEFAULT 0,
            approval INTEGER DEFAULT 0, tag INTEGER DEFAULT 1,
            msg_length INTEGER DEFAULT 0, night_start TEXT DEFAULT '22:00',
            night_end TEXT DEFAULT '06:00', lang TEXT DEFAULT 'en',
            admin_report_target TEXT DEFAULT 'Founder',
            tag_founder INTEGER DEFAULT 0, tag_admins INTEGER DEFAULT 0
        )""")
        
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS badwords (
            chat_id INTEGER, word TEXT, PRIMARY KEY (chat_id, word)
        )""")
        
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS warns (
            chat_id INTEGER, user_id INTEGER, count INTEGER DEFAULT 0,
            PRIMARY KEY (chat_id, user_id)
        )""")
        
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS captchas (
            chat_id INTEGER, user_id INTEGER, answer INTEGER,
            PRIMARY KEY (chat_id, user_id)
        )""")

        self.conn.commit()

    def get_setting(self, chat_id, key):
        self.cursor.execute(f"SELECT {key} FROM group_settings WHERE chat_id=?", (chat_id,))
        row = self.cursor.fetchone()
        if not row:
            self.cursor.execute("INSERT INTO group_settings (chat_id) VALUES (?)", (chat_id,))
            self.conn.commit()
            return self.get_setting(chat_id, key)
        return row[0]

    def set_setting(self, chat_id, key, val):
        self.get_setting(chat_id, "welcome")
        self.cursor.execute(f"UPDATE group_settings SET {key}=? WHERE chat_id=?", (val, chat_id))
        self.conn.commit()

    def toggle_setting(self, chat_id, key):
        cur = self.get_setting(chat_id, key)
        new_val = 0 if cur == 1 else 1
        self.set_setting(chat_id, key, new_val)
        return new_val

    def set_captcha(self, chat_id, user_id, ans):
        self.cursor.execute("INSERT OR REPLACE INTO captchas VALUES (?, ?, ?)", (chat_id, user_id, ans))
        self.conn.commit()

    def get_captcha(self, chat_id, user_id):
        self.cursor.execute("SELECT answer FROM captchas WHERE chat_id=? AND user_id=?", (chat_id, user_id))
        r = self.cursor.fetchone()
        return r[0] if r else None

    def clear_captcha(self, chat_id, user_id):
        self.cursor.execute("DELETE FROM captchas WHERE chat_id=? AND user_id=?", (chat_id, user_id))
        self.conn.commit()

db = DatabaseManager()
