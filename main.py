import asyncio

# Python 3.10+ / Python 3.14 Event Loop Compatibility Fix
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

import os
import re
import time
import json
import sqlite3
import threading
from flask import Flask
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram import Client

# ==========================================
# 🌐 1. KEEP ALIVE WEB SERVER (For Hosting)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "All-in-One Professional Telegram Group Management Bot is Running!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_flask, daemon=True).start()

# ==========================================
# 🗄️ 2. ENHANCED SQLITE DATABASE ENGINE
# ==========================================
class Database:
    def __init__(self, db_file="bot_data.db"):
        self.conn = sqlite3.connect(db_file, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        # Settings Table
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            chat_id INTEGER PRIMARY KEY,
            welcome_text TEXT,
            goodbye_text TEXT,
            rules_text TEXT,
            flood_limit INTEGER DEFAULT 0,
            antiraid INTEGER DEFAULT 0,
            captcha INTEGER DEFAULT 0,
            clean_cmd INTEGER DEFAULT 0,
            clean_service INTEGER DEFAULT 0,
            log_channel INTEGER DEFAULT 0,
            disabled_reports INTEGER DEFAULT 0,
            lang TEXT DEFAULT 'my'
        )
        """)
        # Group Registration Table (For Global Broadcast)
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS groups (
            chat_id INTEGER PRIMARY KEY,
            chat_title TEXT
        )
        """)
        # Filters, Notes, Badwords, Blocklists
        self.cursor.execute("CREATE TABLE IF NOT EXISTS filters (chat_id INTEGER, keyword TEXT, reply_text TEXT, PRIMARY KEY (chat_id, keyword))")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS notes (chat_id INTEGER, note_name TEXT, content TEXT, PRIMARY KEY (chat_id, note_name))")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS badwords (chat_id INTEGER, word TEXT, PRIMARY KEY (chat_id, word))")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS blocklists (chat_id INTEGER, item TEXT, PRIMARY KEY (chat_id, item))")
        
        # Moderation Tables
        self.cursor.execute("CREATE TABLE IF NOT EXISTS approved (chat_id INTEGER, user_id INTEGER, PRIMARY KEY (chat_id, user_id))")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS warns (chat_id INTEGER, user_id INTEGER, count INTEGER DEFAULT 0, PRIMARY KEY (chat_id, user_id))")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS locks (chat_id INTEGER, lock_type TEXT, PRIMARY KEY (chat_id, lock_type))")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS disabled_cmds (chat_id INTEGER, command TEXT, PRIMARY KEY (chat_id, command))")
        self.conn.commit()

    def add_group(self, chat_id, title):
        self.cursor.execute("INSERT OR REPLACE INTO groups (chat_id, chat_title) VALUES (?, ?)", (chat_id, title))
        self.conn.commit()

    def get_all_groups(self):
        self.cursor.execute("SELECT chat_id FROM groups")
        return [r[0] for r in self.cursor.fetchall()]

    def set_setting(self, chat_id, column, value):
        self.cursor.execute(f"INSERT INTO settings (chat_id, {column}) VALUES (?, ?) ON CONFLICT(chat_id) DO UPDATE SET {column}=?", (chat_id, value, value))
        self.conn.commit()

    def get_setting(self, chat_id, column, default=None):
        self.cursor.execute(f"SELECT {column} FROM settings WHERE chat_id=?", (chat_id,))
        res = self.cursor.fetchone()
        return res[0] if res and res[0] is not None else default

    def add_item(self, table, chat_id, key_col, val_col, key_val, val_val=None):
        if val_col:
            self.cursor.execute(f"INSERT OR REPLACE INTO {table} (chat_id, {key_col}, {val_col}) VALUES (?, ?, ?)", (chat_id, key_val, val_val))
        else:
            self.cursor.execute(f"INSERT OR IGNORE INTO {table} (chat_id, {key_col}) VALUES (?, ?)", (chat_id, key_val))
        self.conn.commit()

    def remove_item(self, table, chat_id, key_col, key_val):
        self.cursor.execute(f"DELETE FROM {table} WHERE chat_id=? AND {key_col}=?", (chat_id, key_val))
        self.conn.commit()

    def get_items(self, table, chat_id, col):
        self.cursor.execute(f"SELECT {col} FROM {table} WHERE chat_id=?", (chat_id,))
        return [r[0] for r in self.cursor.fetchall()]

    def get_kv_items(self, table, chat_id, k_col, v_col):
        self.cursor.execute(f"SELECT {k_col}, {v_col} FROM {table} WHERE chat_id=?", (chat_id,))
        return dict(self.cursor.fetchall())

db = Database()

# ==========================================
# 🔑 3. CONFIG & INITIALIZATION
# ==========================================
BOT_TOKEN = "8886077155:AAET1U9CXGZtaiIBLYxAutzFKFe-BkQpVno"
API_ID = 31788996
API_HASH = "0c6714a879b2b1abba75dc4526521ca8"
OWNER_IDS = [7974865879, 7177628115, 8438417346]

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")
userbot = Client("myuserbot", api_id=API_ID, api_hash=API_HASH)

def start_userbot():
    try:
        userbot.start()
        print("✅ Pyrogram Userbot Started Successfully.")
    except Exception as e:
        print(f"⚠️ Userbot Client Warning: {e}")

threading.Thread(target=start_userbot, daemon=True).start()

user_flood_tracker = {}
mention_cancel_flags = {}

# ==========================================
# 🔗 4. BUTTON LINK PARSER FUNCTION
# ==========================================
def parse_button_links(text):
    if not text:
        return "", None
    pattern = r'\[([^\]]+)\]\(buttonurl://([^\)]+)\)'
    buttons = re.findall(pattern, text)
    clean_text = re.sub(pattern, '', text).strip()
    
    if not buttons:
        return clean_text, None

    markup = InlineKeyboardMarkup()
    row = []
    for btn_name, btn_url in buttons:
        same_row = False
        if btn_url.endswith(':same'):
            btn_url = btn_url[:-5]
            same_row = True

        button = InlineKeyboardButton(text=btn_name, url=btn_url)
        if same_row and row:
            row.append(button)
        else:
            if row:
                markup.add(*row)
                row = []
            row.append(button)
            
    if row:
        markup.add(*row)

    return clean_text, markup

# ==========================================
# 🛡️ 5. HELPER PERMISSIONS & LOGGING
# ==========================================
def is_owner(user_id):
    return user_id in OWNER_IDS

def is_admin(chat_id, user_id):
    if is_owner(user_id) or chat_id == user_id:
        return True
    try:
        m = bot.get_chat_member(chat_id, user_id)
        return m.status in ['administrator', 'creator']
    except Exception:
        return False

# ==========================================
# 🚀 6. ALL 21 COMPLETE MODULES LOGIC
# ==========================================

# 1. Admin List & Sudo Management
@bot.message_handler(commands=['admin', 'admins', 'addsudo', 'rmsudo'])
def module_admin(message):
    if 'addsudo' in message.text or 'rmsudo' in message.text:
        if not is_owner(message.from_user.id):
            return bot.reply_to(message, "❌ Bot Owner သာလျှင် Sudo စီမံနိုင်ပါသည်။")
        if message.reply_to_message:
            target_id = message.reply_to_message.from_user.id
            if 'addsudo' in message.text:
                if target_id not in OWNER_IDS: OWNER_IDS.append(target_id)
                bot.reply_to(message, f"👑 User `{target_id}` အား Sudo ထဲသို့ ထည့်ပြီးပါပြီ။")
            else:
                if target_id in OWNER_IDS: OWNER_IDS.remove(target_id)
                bot.reply_to(message, f"🗑️ User `{target_id}` အား Sudo မှ ဖယ်ထုတ်ပြီးပါပြီ။")
        return

    admins = bot.get_chat_administrators(message.chat.id)
    admin_list = "\n".join([f"• [{a.user.first_name}](tg://user?id={a.user.id})" for a in admins])
    bot.reply_to(message, f"👑 **Group Admin စာရင်း:**\n\n{admin_list}")

# 2. Antiflood
@bot.message_handler(commands=['setflood', 'flood'])
def module_antiflood(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    parts = message.text.split()
    if len(parts) > 1 and parts[1].isdigit():
        limit = int(parts[1])
        db.set_setting(message.chat.id, "flood_limit", limit)
        bot.reply_to(message, f"🛡️ Antiflood Limit ကို `{limit}` စာစောင်အဖြစ် သတ်မှတ်လိုက်ပါပြီ။ (0 = ပိတ်ရန်)")
    else:
        curr = db.get_setting(message.chat.id, "flood_limit", 0)
        bot.reply_to(message, f"🛡️ **လက်ရှိ Antiflood Limit:** `{curr}`\nပြောင်းရန်: `/setflood 5` (၅ စက္ကန့်အတွင်း စာ limit)")

# 3. Antiraid
@bot.message_handler(commands=['antiraid'])
def module_antiraid(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    parts = message.text.split()
    status = 1 if len(parts) > 1 and parts[1].lower() == 'on' else 0
    db.set_setting(message.chat.id, "antiraid", status)
    bot.reply_to(message, f"🛡️ **Anti-Raid Mode:** `{'ON' if status else 'OFF'}`")

# 4. Approval System
@bot.message_handler(commands=['approve', 'unapprove', 'approved'])
def module_approval(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    chat_id = message.chat.id

    if 'approved' in message.text:
        users = db.get_items("approved", chat_id, "user_id")
        u_str = "\n".join([f"• `{u}`" for u in users])
        bot.reply_to(message, f"✅ **Approved Members စာရင်း:**\n{u_str if u_str else 'မရှိပါ'}")
        return

    if not message.reply_to_message:
        return bot.reply_to(message, "⚠️ Approve / Unapprove ပေးလိုသော User ၏ Message ကို Reply ပြန်ပါ။")

    uid = message.reply_to_message.from_user.id
    if 'unapprove' in message.text:
        db.remove_item("approved", chat_id, "user_id", uid)
        bot.reply_to(message, f"❌ User `{uid}` အား Approved စာရင်းမှ ဖယ်လိုက်ပါပြီ။")
    else:
        db.add_item("approved", chat_id, "user_id", None, uid)
        bot.reply_to(message, f"✅ User `{uid}` အား Approved စာရင်းသို့ ထည့်လိုက်ပါပြီ။ (Bot ၏ ကန့်သတ်ချက်များမှ ကင်းလွတ်မည်)")

# 5. Bans, Unban, Mute, Unmute, Kick
@bot.message_handler(commands=['ban', 'unban', 'mute', 'unmute', 'kick'])
def module_bans(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    if not message.reply_to_message:
        return bot.reply_to(message, "⚠️ ပြုလုပ်လိုသော User ၏ စာကို Reply ပြန်ပါ။")

    uid = message.reply_to_message.from_user.id
    cmd = message.text.split()[0].replace('/', '').lower()

    try:
        if cmd == 'ban':
            bot.ban_chat_member(message.chat.id, uid)
            bot.reply_to(message, "🚫 User အား Ban လိုက်ပါပြီ။")
        elif cmd == 'unban':
            bot.unban_chat_member(message.chat.id, uid, only_if_banned=True)
            bot.reply_to(message, "✅ User အား Unban ပေးလိုက်ပါပြီ။")
        elif cmd == 'mute':
            bot.restrict_chat_member(message.chat.id, uid, can_send_messages=False)
            bot.reply_to(message, "🔇 User အား Mute လိုက်ပါပြီ။")
        elif cmd == 'unmute':
            bot.restrict_chat_member(message.chat.id, uid, can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True)
            bot.reply_to(message, "🔊 User အား Unmute ပေးလိုက်ပါပြီ။")
        elif cmd == 'kick':
            bot.ban_chat_member(message.chat.id, uid)
            bot.unban_chat_member(message.chat.id, uid)
            bot.reply_to(message, "👞 User အား Group မှ Kick ထုတ်လိုက်ပါပြီ။")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: `{e}`")

# 6. Blocklists & 20. Badwords
@bot.message_handler(commands=['addbad', 'rmbad', 'addblock', 'rmblock', 'badwords', 'blocklist'])
def module_blocklists_badwords(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    chat_id = message.chat.id
    cmd = message.text.split()[0].replace('/', '').lower()

    if cmd in ['badwords', 'blocklist']:
        tbl = "badwords" if cmd == 'badwords' else "blocklists"
        col = "word" if cmd == 'badwords' else "item"
        items = db.get_items(tbl, chat_id, col)
        i_str = ", ".join([f"`{w}`" for w in items])
        bot.reply_to(message, f"🚫 **{cmd.upper()} စာရင်း:**\n{i_str if i_str else 'မရှိပါ'}")
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return bot.reply_to(message, f"⚠️ **Usage:** `/{cmd} <word/link>`")

    val = parts[1].lower()
    tbl = "badwords" if 'bad' in cmd else "blocklists"
    col = "word" if 'bad' in cmd else "item"

    if 'rm' in cmd:
        db.remove_item(tbl, chat_id, col, val)
        bot.reply_to(message, f"🗑️ `{val}` အား စာရင်းမှ ဖျက်လိုက်ပါပြီ။")
    else:
        db.add_item(tbl, chat_id, col, None, val)
        bot.reply_to(message, f"🚫 `{val}` အား စာရင်းသို့ ထည့်လိုက်ပါပြီ။")

# 7. Disabling Commands
@bot.message_handler(commands=['disable', 'enable', 'disabled'])
def module_disabling(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    chat_id = message.chat.id
    parts = message.text.split()

    if parts[0] == '/disabled':
        cmds = db.get_items("disabled_cmds", chat_id, "command")
        c_str = ", ".join(cmds)
        return bot.reply_to(message, f"🚫 **Disabled Commands:**\n{c_str if c_str else 'မရှိပါ'}")

    if len(parts) < 2:
        return bot.reply_to(message, "⚠️ **Usage:** `/disable <command>` သို့မဟုတ် `/enable <command>`")

    target_cmd = parts[1].replace('/', '').lower()
    if 'enable' in parts[0]:
        db.remove_item("disabled_cmds", chat_id, "command", target_cmd)
        bot.reply_to(message, f"✅ `/{target_cmd}` ကို ပြန်လည်ဖွင့်ပေးလိုက်ပါပြီ။")
    else:
        db.add_item("disabled_cmds", chat_id, "command", None, target_cmd)
        bot.reply_to(message, f"🚫 `/{target_cmd}` ကို ပိတ်လိုက်ပါပြီ။")

# 8. Filters & 13. Notes (With Button Link Support)
@bot.message_handler(commands=['filter', 'stop', 'save', 'clear', 'notes', 'filters'])
def module_filters_notes(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    chat_id = message.chat.id
    cmd = message.text.split()[0].replace('/', '').lower()

    if cmd == 'notes':
        notes = db.get_items("notes", chat_id, "note_name")
        n_str = "\n".join([f"• `#{n}`" for n in notes])
        return bot.reply_to(message, f"📝 **Saved Notes:**\n{n_str if n_str else 'မရှိပါ'}")

    if cmd == 'filters':
        filts = db.get_items("filters", chat_id, "keyword")
        f_str = "\n".join([f"• `{f}`" for f in filts])
        return bot.reply_to(message, f"🔍 **Active Filters:**\n{f_str if f_str else 'မရှိပါ'}")

    parts = message.text.split(maxsplit=2)
    if len(parts) < 2:
        return bot.reply_to(message, "⚠️ **Usage:** `/save <note_name> <text>` သို့မဟုတ် `/filter <keyword> <text>`\n\n*(Button ပါထည့်လိုပါက `[Text](buttonurl://https://link.com)` ဟု ရေးနိုင်ပါသည်။)*")

    key = parts[1].lower()
    if cmd in ['clear', 'stop']:
        if cmd == 'clear': db.remove_item("notes", chat_id, "note_name", key)
        else: db.remove_item("filters", chat_id, "keyword", key)
        return bot.reply_to(message, f"🗑️ `{key}` အား ဖျက်လိုက်ပါပြီ။")

    if len(parts) < 3: return
    content = parts[2]

    if cmd == 'save':
        db.add_item("notes", chat_id, "note_name", "content", key, content)
        bot.reply_to(message, f"📝 Note `#{key}` သိမ်းဆည်းပြီးပါပြီ။")
    elif cmd == 'filter':
        db.add_item("filters", chat_id, "keyword", "reply_text", key, content)
        bot.reply_to(message, f"🔍 Filter `{key}` သတ်မှတ်ပြီးပါပြီ။")

# 9. Formatting Guide
@bot.message_handler(commands=['markdown', 'formatting'])
def module_formatting(message):
    guide = (
        "✨ **Formatting Guide & Button Link Syntax:**\n\n"
        "• *Bold* -> `*text*`\n"
        "• _Italic_ -> `_text_`\n"
        "• `Monospace` -> `` `text` ``\n"
        "• [Hyperlink](https://google.com) -> `[Text](url)`\n\n"
        "🔘 **Inline Button Links:**\n"
        "`[Button Title](buttonurl://https://yourlink.com)`\n\n"
        "🔘 **တစ်တန်းတည်း မလ်တီ ခလုတ်များ:**\n"
        "`[Btn 1](buttonurl://https://link1.com) [Btn 2](buttonurl://https://link2.com:same)`"
    )
    bot.reply_to(message, guide)

# 10. Greetings (Welcome & Goodbye with Button Support)
@bot.message_handler(commands=['setwelcome', 'setgoodbye', 'welcome', 'goodbye'])
def module_greetings(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    chat_id = message.chat.id
    parts = message.text.split(maxsplit=1)
    cmd = parts[0].replace('/', '').lower()

    if cmd == 'setwelcome':
        if len(parts) > 1:
            db.set_setting(chat_id, "welcome_text", parts[1])
            txt, markup = parse_button_links(parts[1])
            bot.reply_to(message, f"👋 **Welcome Message သတ်မှတ်ပြီးပါပြီ:**\n\n{txt}", reply_markup=markup)
        else:
            bot.reply_to(message, "⚠️ **Usage:** `/setwelcome ကြိုဆိုပါတယ်! [Channel](buttonurl://https://t.me/xxx)`")

    elif cmd == 'setgoodbye':
        if len(parts) > 1:
            db.set_setting(chat_id, "goodbye_text", parts[1])
            txt, markup = parse_button_links(parts[1])
            bot.reply_to(message, f"👋 **Goodbye Message သတ်မှတ်ပြီးပါပြီ:**\n\n{txt}", reply_markup=markup)
        else:
            bot.reply_to(message, "⚠️ **Usage:** `/setgoodbye သွားတော့နော်! [Website](buttonurl://https://xxx.com)`")

# 11. Locks System
@bot.message_handler(commands=['lock', 'unlock', 'locks'])
def module_locks(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    chat_id = message.chat.id

    if message.text == '/locks':
        locks = db.get_items("locks", chat_id, "lock_type")
        l_str = ", ".join(locks)
        return bot.reply_to(message, f"🔒 **Locked Types:**\n{l_str if l_str else 'မရှိပါ'}")

    parts = message.text.split()
    if len(parts) < 2:
        return bot.reply_to(message, "⚠️ **Usage:** `/lock stickers` (သို့မဟုတ် `links`, `media`)")

    ltype = parts[1].lower()
    if 'unlock' in parts[0]:
        db.remove_item("locks", chat_id, "lock_type", ltype)
        bot.reply_to(message, f"🔓 `{ltype}` ကို ပြန်လည်ဖွင့်ပေးလိုက်ပါပြီ။")
    else:
        db.add_item("locks", chat_id, "lock_type", None, ltype)
        bot.reply_to(message, f"🔒 `{ltype}` ကို ပိတ်လိုက်ပါပြီ။")

# 12. Misc Module
@bot.message_handler(commands=['id', 'info'])
def module_misc(message):
    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    info = (
        f"ℹ️ **User Information:**\n\n"
        f"👤 First Name: {target.first_name}\n"
        f"🆔 User ID: `{target.id}`\n"
        f"💬 Group Chat ID: `{message.chat.id}`"
    )
    bot.reply_to(message, info)

# 14. Pin Module
@bot.message_handler(commands=['pin', 'unpin'])
def module_pin(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    if message.reply_to_message:
        try:
            if 'unpin' in message.text:
                bot.unpin_chat_message(message.chat.id, message.reply_to_message.message_id)
                bot.reply_to(message, "📌 Unpinned Success!")
            else:
                bot.pin_chat_message(message.chat.id, message.reply_to_message.message_id)
                bot.reply_to(message, "📌 Pinned Success!")
        except Exception as e:
            bot.reply_to(message, f"❌ Pin Error: `{e}`")

# 15. Privacy Policy
@bot.message_handler(commands=['privacy'])
def module_privacy(message):
    bot.reply_to(message, "🔒 **Privacy Policy:** ဒီ Bot သည် Group စီမံခန့်ခွဲရန်အတွက် အချက်အလက်များ (Settings, Notes, Filters) များကို SQLite Database တွင် လုံခြုံစွာ သိမ်းဆည်းပါသည်။ Personal Data များကို သီးသန့်ရယူခြင်း မရှိပါ။")

# 16. Reports System & 17. Rules
@bot.message_handler(commands=['report', 'reports', 'rules', 'setrules'])
def module_rules_reports(message):
    chat_id = message.chat.id
    parts = message.text.split(maxsplit=1)

    if 'reports' in parts[0] and is_admin(chat_id, message.from_user.id):
        status = 1 if len(parts) > 1 and parts[1].lower() == 'off' else 0
        db.set_setting(chat_id, "disabled_reports", status)
        return bot.reply_to(message, f"📢 User Reports: `{'OFF' if status else 'ON'}`")

    if 'report' in parts[0]:
        if db.get_setting(chat_id, "disabled_reports", 0) == 1: return
        if message.reply_to_message:
            admins = bot.get_chat_administrators(chat_id)
            mentions = " ".join([f"[{a.user.first_name}](tg://user?id={a.user.id})" for a in admins])
            bot.reply_to(message.reply_to_message, f"🚨 **Reported to Admins!**\n{mentions}")
        return

    if 'setrules' in parts[0] and is_admin(chat_id, message.from_user.id):
        if len(parts) > 1:
            db.set_setting(chat_id, "rules_text", parts[1])
            bot.reply_to(message, "📜 Group Rules အား သတ်မှတ်လိုက်ပါပြီ။")
    elif 'rules' in parts[0]:
        rule_txt = db.get_setting(chat_id, "rules_text", "📜 **Rules မသတ်မှတ်ရသေးပါ။**")
        txt, markup = parse_button_links(rule_txt)
        bot.reply_to(message, txt, reply_markup=markup)

# 18. Warnings System
@bot.message_handler(commands=['warn', 'warns', 'resetwarns'])
def module_warns(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    if not message.reply_to_message: return

    uid = message.reply_to_message.from_user.id
    chat_id = message.chat.id
    cmd = message.text.split()[0].replace('/', '').lower()

    db.cursor.execute("SELECT count FROM warns WHERE chat_id=? AND user_id=?", (chat_id, uid))
    res = db.cursor.fetchone()
    curr_warns = res[0] if res else 0

    if cmd == 'warns':
        return bot.reply_to(message, f"⚠️ User `{uid}` Warning Status: `{curr_warns}/3`")
    elif cmd == 'resetwarns':
        db.remove_item("warns", chat_id, "user_id", uid)
        return bot.reply_to(message, "✅ User ၏ Warnings များအား Reset လုပ်လိုက်ပါပြီ။")

    curr_warns += 1
    if curr_warns >= 3:
        bot.ban_chat_member(chat_id, uid)
        db.remove_item("warns", chat_id, "user_id", uid)
        bot.reply_to(message, f"🚨 User ၏ Warn Limit (3/3) ပြည့်သွားသဖြင့် Ban လိုက်ပါပြီ။")
    else:
        db.add_item("warns", chat_id, "user_id", "count", uid, curr_warns)
        bot.reply_to(message, f"⚠️ User အား သတိပေးလိုက်ပါပြီ (Warn Status: {curr_warns}/3)")

# 21. Global Broadcast to All Joined Groups (With Multi-Button Link Support)
@bot.message_handler(commands=['broadcast'])
def module_broadcast(message):
    if not is_owner(message.from_user.id):
        return bot.reply_to(message, "❌ Bot Owner သာလျှင် Broadcast ပို့နိုင်ပါသည်။")

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return bot.reply_to(message, "⚠️ **Usage:** `/broadcast <စာသားများ> [Button Title](buttonurl://https://link.com)`")

    raw_text = parts[1]
    clean_txt, markup = parse_button_links(raw_text)

    all_groups = db.get_all_groups()
    success = 0
    failed = 0

    status_msg = bot.reply_to(message, f"📢 Groups ပေါင်း `{len(all_groups)}` ခုသို့ ကြော်ငြာ စတင်ပို့နေပါပြီ...")

    for g_id in all_groups:
        try:
            bot.send_message(g_id, clean_txt, reply_markup=markup)
            success += 1
            time.sleep(0.3)
        except Exception:
            failed += 1

    bot.edit_message_text(f"✅ **Broadcast ပို့ဆောင်ပြီးပါပြီ!**\n\n🎯 အောင်မြင်သည့် Group: `{success}`\n❌ မအောင်မြင်သည့် Group: `{failed}`", message.chat.id, status_msg.message_id)

# 19. Help Menu & Callbacks
@bot.message_handler(commands=['start', 'help'])
def module_help(message):
    main_markup = InlineKeyboardMarkup(row_width=2)
    buttons = [
        InlineKeyboardButton("👑 Admin & Bans", callback_data="page_1"),
        InlineKeyboardButton("🛡️ Flood & Blocks", callback_data="page_2"),
        InlineKeyboardButton("⚙️ Filters & Notes", callback_data="page_3"),
        InlineKeyboardButton("🌐 Locks & Misc", callback_data="page_4"),
        InlineKeyboardButton("📜 Rules & Warns", callback_data="page_5"),
        InlineKeyboardButton("📢 Broadcast & Buttons", callback_data="page_6")
    ]
    main_markup.add(*buttons)
    bot.reply_to(message, "👋 **Group Management Bot ၏ Commands များကြည့်ရန် အောက်ပါ Button များကို နှိပ်ပါ:**", reply_markup=main_markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('page_'))
def handle_help_pages(call: CallbackQuery):
    page = call.data.split('_')[1]
    back_markup = InlineKeyboardMarkup()
    back_markup.add(InlineKeyboardButton("⬅️ ပင်မ Menu သို့", callback_data="page_main"))

    pages_content = {
        "main": "👋 **Group Management Bot ၏ Commands များကြည့်ရန် အောက်ပါ Button များကို နှိပ်ပါ:**",
        "1": "📌 **Admin & Moderation:**\n\n• `/admin` - Admin စာရင်းကြည့်ရန်\n• `/ban`, `/unban`, `/mute`, `/unmute`, `/kick` - အဖွဲ့ဝင်များကို အရေးယူရန်\n• `/approve`, `/unapprove`, `/approved` - Approval စနစ်",
        "2": "📌 **Flood & Blocklists:**\n\n• `/setflood <num>` - Flood ကန့်သတ်ရန်\n• `/antiraid on/off` - Anti Raid\n• `/addbad <word>`, `/badwords` - Badwords ပိတ်ရန်\n• `/addblock <item>`, `/blocklist` - Blocklist ပြုလုပ်ရန်",
        "3": "📌 **Filters & Notes:**\n\n• `/save <note> <text>` - Note သိမ်းရန်\n• `/notes`, `/clear <note>` - Notes ကြည့်/ဖျက်ရန်\n• `/filter <key> <text>` - Filter သတ်မှတ်ရန်\n• `/stop <key>` - Filter ဖျက်ရန်",
        "4": "📌 **Locks & Misc:**\n\n• `/lock <type>`, `/unlock` - Stickers/Links/Media ပိတ်ရန်\n• `/locks` - ပိတ်ထားသည်များ ကြည့်ရန်\n• `/id`, `/info` - User Info ကြည့်ရန်\n• `/markdown` - Formatting လမ်းညွှန်",
        "5": "📌 **Rules, Reports & Warns:**\n\n• `/setrules <text>`, `/rules` - Group စည်းကမ်းများ\n• `/report` - Admin သို့ တိုင်ကြားရန်\n• `/warn`, `/warns`, `/resetwarns` - Warning စနစ်",
        "6": "📌 **Broadcast & Button Link Syntax:**\n\n• `/broadcast <text>` - Bot ရှိသော Group အားလုံးသို့ ကြော်ငြာပို့ရန် (Owner သာ)\n\n🔘 **Button Link ထည့်နည်း:**\n`[ခလုတ်အမည်](buttonurl://https://yourlink.com)`"
    }

    text_to_show = pages_content.get(page, "ℹ️ အချက်အလက် မရှိပါ။")

    try:
        if page == "main":
            main_markup = InlineKeyboardMarkup(row_width=2)
            buttons = [
                InlineKeyboardButton("👑 Admin & Bans", callback_data="page_1"),
                InlineKeyboardButton("🛡️ Flood & Blocks", callback_data="page_2"),
                InlineKeyboardButton("⚙️ Filters & Notes", callback_data="page_3"),
                InlineKeyboardButton("🌐 Locks & Misc", callback_data="page_4"),
                InlineKeyboardButton("📜 Rules & Warns", callback_data="page_5"),
                InlineKeyboardButton("📢 Broadcast & Buttons", callback_data="page_6")
            ]
            main_markup.add(*buttons)
            bot.edit_message_text(text_to_show, call.message.chat.id, call.message.message_id, reply_markup=main_markup)
        else:
            bot.edit_message_text(text_to_show, call.message.chat.id, call.message.message_id, reply_markup=back_markup)
    except Exception: pass

# ==========================================
# 🔄 7. AUTOMATION & LISTENER ENGINE
# ==========================================
@bot.message_handler(func=lambda message: True, content_types=['text', 'new_chat_members', 'left_chat_member', 'sticker', 'document', 'photo'])
def global_automation_handler(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    # Register Group Chat ID for Broadcast
    if message.chat.type in ['group', 'supergroup']:
        db.add_group(chat_id, message.chat.title)

    approved_list = db.get_items("approved", chat_id, "user_id")
    is_user_approved = user_id in approved_list

    # 1. Welcome & Goodbye Messages
    if message.content_type == 'new_chat_members':
        welc_text = db.get_setting(chat_id, "welcome_text", None)
        if welc_text:
            txt, markup = parse_button_links(welc_text)
            bot.send_message(chat_id, txt, reply_markup=markup)
        return

    if message.content_type == 'left_chat_member':
        gb_text = db.get_setting(chat_id, "goodbye_text", None)
        if gb_text:
            txt, markup = parse_button_links(gb_text)
            bot.send_message(chat_id, txt, reply_markup=markup)
        return

    # 2. Locks Enforcement
    if not is_user_approved and not is_admin(chat_id, user_id):
        locks = db.get_items("locks", chat_id, "lock_type")
        if 'stickers' in locks and message.content_type == 'sticker':
            try: bot.delete_message(chat_id, message.message_id)
            except Exception: pass
            return
        if 'links' in locks and message.text and ("http://" in message.text or "https://" in message.text or "t.me" in message.text):
            try: bot.delete_message(chat_id, message.message_id)
            except Exception: pass
            return

    # 3. Disabling Commands Engine
    if message.text and message.text.startswith('/'):
        cmd_name = message.text.split()[0].replace('/', '').lower()
        disabled_list = db.get_items("disabled_cmds", chat_id, "command")
        if cmd_name in disabled_list:
            bot.reply_to(message, "❌ ဒီ Command အား Admin မှ ပိတ်ထားပါသည်။")
            return

    # 4. Badwords Auto Filter
    if message.text and not is_user_approved:
        text_lower = message.text.lower()
        badwords = db.get_items("badwords", chat_id, "word")
        for word in badwords:
            if word in text_lower:
                try:
                    bot.delete_message(chat_id, message.message_id)
                    bot.send_message(chat_id, f"⚠️ [{message.from_user.first_name}](tg://user?id={user_id}) ပိတ်ပင်ထားသော စာလုံး သုံးနှုန်းသဖြင့် စာအား ဖျက်လိုက်ပါပြီ။")
                    return
                except Exception: pass

        # 5. Anti-Flood Control
        limit = db.get_setting(chat_id, "flood_limit", 0)
        if limit > 0 and not is_admin(chat_id, user_id):
            now = time.time()
            if chat_id not in user_flood_tracker: user_flood_tracker[chat_id] = {}
            if user_id not in user_flood_tracker[chat_id]: user_flood_tracker[chat_id][user_id] = []

            timestamps = [t for t in user_flood_tracker[chat_id][user_id] if now - t < 5]
            timestamps.append(now)
            user_flood_tracker[chat_id][user_id] = timestamps

            if len(timestamps) >= limit:
                bot.restrict_chat_member(chat_id, user_id, can_send_messages=False)
                bot.send_message(chat_id, f"🔇 [{message.from_user.first_name}](tg://user?id={user_id}) စာစောင်များစွာ ဆက်တိုက် ပို့သဖြင့် Mute လိုက်ပါပြီ။")
                user_flood_tracker[chat_id][user_id] = []
                return

        # 6. Notes (#notename) & Filters Trigger
        if text_lower.startswith("#"):
            note_key = text_lower[1:]
            notes = db.get_kv_items("notes", chat_id, "note_name", "content")
            if note_key in notes:
                txt, markup = parse_button_links(notes[note_key])
                bot.reply_to(message, txt, reply_markup=markup)
        else:
            filters = db.get_kv_items("filters", chat_id, "keyword", "reply_text")
            for f_key, f_val in filters.items():
                if f_key in text_lower:
                    txt, markup = parse_button_links(f_val)
                    bot.reply_to(message, txt, reply_markup=markup)

# ==========================================
# 🚀 8. BOT INFINITY POLLING
# ==========================================
if __name__ == '__main__':
    print("🤖 Fully Loaded Telegram Management Engine Active!")
    bot.infinity_polling(skip_pending=True)
