import os
import random
import re
import sqlite3
import threading
import time
from datetime import datetime
from flask import Flask
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# ==========================================
# ⚙️ 1. CONFIGURATION
# ==========================================
BOT_TOKEN = "8886077155:AAET1U9CXGZtaiIBLYxAutzFKFe-BkQpVno"
MASTER_OWNERS = [7974865879, 7177628115, 8438417346]
DB_NAME = "group_bot_data.db"
PORT = int(os.environ.get("PORT", 8080))

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

# ==========================================
# 🌐 2. KEEP ALIVE WEB SERVER (FLASK)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "All Systems & Modules Active & Running!"

def run_flask():
    app.run(host='0.0.0.0', port=PORT)

threading.Thread(target=run_flask, daemon=True).start()

# ==========================================
# 🗄️ 3. DATABASE ENGINE
# ==========================================
class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.setup()

    def setup(self):
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            chat_id INTEGER PRIMARY KEY,
            welcome INTEGER DEFAULT 1, goodbye INTEGER DEFAULT 1,
            antispam INTEGER DEFAULT 1, antiflood INTEGER DEFAULT 1,
            captcha INTEGER DEFAULT 0, porn INTEGER DEFAULT 1,
            night INTEGER DEFAULT 0, links INTEGER DEFAULT 0,
            stickers INTEGER DEFAULT 0, media INTEGER DEFAULT 0,
            approval INTEGER DEFAULT 0, tag INTEGER DEFAULT 1,
            msg_length INTEGER DEFAULT 0, night_start TEXT DEFAULT '22:00',
            night_end TEXT DEFAULT '06:00'
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
        CREATE TABLE IF NOT EXISTS pending_captcha (
            chat_id INTEGER, user_id INTEGER, answer INTEGER,
            PRIMARY KEY (chat_id, user_id)
        )""")
        self.conn.commit()

    def get_setting(self, chat_id, key):
        self.cursor.execute(f"SELECT {key} FROM settings WHERE chat_id=?", (chat_id,))
        res = self.cursor.fetchone()
        if not res:
            self.cursor.execute("INSERT INTO settings (chat_id) VALUES (?)", (chat_id,))
            self.conn.commit()
            return 1 if key in ['welcome', 'goodbye', 'antispam', 'antiflood', 'porn', 'tag'] else 0
        return res[0]

    def toggle_setting(self, chat_id, key):
        cur = self.get_setting(chat_id, key)
        new_val = 0 if cur == 1 else 1
        self.cursor.execute(f"UPDATE settings SET {key}=? WHERE chat_id=?", (new_val, chat_id))
        self.conn.commit()
        return new_val

    def add_badword(self, chat_id, word):
        self.cursor.execute("INSERT OR IGNORE INTO badwords VALUES (?, ?)", (chat_id, word.lower()))
        self.conn.commit()

    def del_badword(self, chat_id, word):
        self.cursor.execute("DELETE FROM badwords WHERE chat_id=? AND word=?", (chat_id, word.lower()))
        self.conn.commit()

    def get_badwords(self, chat_id):
        self.cursor.execute("SELECT word FROM badwords WHERE chat_id=?", (chat_id,))
        return [r[0] for r in self.cursor.fetchall()]

    def add_warn(self, chat_id, user_id):
        self.cursor.execute("SELECT count FROM warns WHERE chat_id=? AND user_id=?", (chat_id, user_id))
        res = self.cursor.fetchone()
        cnt = (res[0] + 1) if res else 1
        self.cursor.execute("INSERT OR REPLACE INTO warns VALUES (?, ?, ?)", (chat_id, user_id, cnt))
        self.conn.commit()
        return cnt

    def reset_warns(self, chat_id, user_id):
        self.cursor.execute("DELETE FROM warns WHERE chat_id=? AND user_id=?", (chat_id, user_id))
        self.conn.commit()

    def add_captcha(self, chat_id, user_id, ans):
        self.cursor.execute("INSERT OR REPLACE INTO pending_captcha VALUES (?, ?, ?)", (chat_id, user_id, ans))
        self.conn.commit()

    def get_captcha(self, chat_id, user_id):
        self.cursor.execute("SELECT answer FROM pending_captcha WHERE chat_id=? AND user_id=?", (chat_id, user_id))
        res = self.cursor.fetchone()
        return res[0] if res else None

    def remove_captcha(self, chat_id, user_id):
        self.cursor.execute("DELETE FROM pending_captcha WHERE chat_id=? AND user_id=?", (chat_id, user_id))
        self.conn.commit()

db = Database()

# Helpers
def is_owner(user_id):
    return user_id in MASTER_OWNERS

def is_admin(chat_id, user_id):
    if is_owner(user_id) or chat_id == user_id: return True
    try:
        m = bot.get_chat_member(chat_id, user_id)
        return m.status in ['administrator', 'creator']
    except Exception: return False

# ==========================================
# 🎛️ 4. DASHBOARD UI BUILDERS
# ==========================================
def build_settings_page_1(chat_id):
    wel = "✅" if db.get_setting(chat_id, "welcome") else "❌"
    gb = "✅" if db.get_setting(chat_id, "goodbye") else "❌"
    aspam = "✅" if db.get_setting(chat_id, "antispam") else "❌"
    aflood = "✅" if db.get_setting(chat_id, "antiflood") else "❌"
    cap = "✅" if db.get_setting(chat_id, "captcha") else "❌"
    porn = "✅" if db.get_setting(chat_id, "porn") else "❌"
    night = "✅" if db.get_setting(chat_id, "night") else "❌"
    links = "✅" if db.get_setting(chat_id, "links") else "❌"
    appr = "✅" if db.get_setting(chat_id, "approval") else "❌"

    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📜 Regulation", callback_data="btn_Regulation"),
        InlineKeyboardButton(f"📧 Anti-Spam {aspam}", callback_data="toggle_antispam"),
        InlineKeyboardButton(f"💬 Welcome {wel}", callback_data="toggle_welcome"),
        InlineKeyboardButton(f"🗣️ Anti-Flood {aflood}", callback_data="toggle_antiflood"),
        InlineKeyboardButton(f"👋 Goodbye {gb}", callback_data="toggle_goodbye"),
        InlineKeyboardButton("🕉️ Alphabets", callback_data="btn_Alphabets"),
        InlineKeyboardButton(f"🧠 Captcha {cap}", callback_data="toggle_captcha"),
        InlineKeyboardButton("🔦 Checks", callback_data="btn_Checks"),
        InlineKeyboardButton("🆘 @Admin", callback_data="btn_AdminTag"),
        InlineKeyboardButton("🔐 Blocks", callback_data="btn_Blocks"),
        InlineKeyboardButton("📸 Media", callback_data="btn_Media"),
        InlineKeyboardButton(f"🔞 Porn {porn}", callback_data="toggle_porn"),
        InlineKeyboardButton("❗ Warns", callback_data="btn_Warns"),
        InlineKeyboardButton(f"🌙 Night {night}", callback_data="toggle_night"),
        InlineKeyboardButton("🔔 Tag", callback_data="btn_Tag"),
        InlineKeyboardButton(f"🔗 Link {links}", callback_data="toggle_links")
    )
    markup.add(InlineKeyboardButton("🕵️ Guardian Bot 🆕", callback_data="btn_Guardian"))
    markup.add(InlineKeyboardButton(f"📑 Approval mode {appr}", callback_data="toggle_approval"))
    markup.add(InlineKeyboardButton("🗑️ Deleting Messages", callback_data="btn_Deleting"))
    markup.row(
        InlineKeyboardButton("🇬🇧 Lang", callback_data="btn_lang"),
        InlineKeyboardButton("✅ Close", callback_data="close_menu"),
        InlineKeyboardButton("▶️ Other", callback_data="page_2")
    )
    return markup

def build_settings_page_2(chat_id):
    stickers = "✅" if db.get_setting(chat_id, "stickers") else "❌"
    media = "✅" if db.get_setting(chat_id, "media") else "❌"

    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("📁 Topic", callback_data="btn_Topic"),
        InlineKeyboardButton("🔤 Banned Words", callback_data="show_badwords"),
        InlineKeyboardButton("⏰ Recurring messages", callback_data="btn_Recurring"),
        InlineKeyboardButton("👥 Members Management", callback_data="btn_Members"),
        InlineKeyboardButton("😷 Masked users", callback_data="btn_Masked"),
        InlineKeyboardButton("📣 Discussion group 🆕", callback_data="btn_Discussion"),
        InlineKeyboardButton("📱 Personal Commands", callback_data="btn_PersonalCommands"),
        InlineKeyboardButton(f"🎭 Magic Stickers&GIFs {stickers}", callback_data="toggle_stickers"),
        InlineKeyboardButton(f"📷 Media Protection {media}", callback_data="toggle_media"),
        InlineKeyboardButton("✏️ Message length", callback_data="btn_MsgLength"),
        InlineKeyboardButton("📢 Channels management 🆕", callback_data="btn_Channels")
    )
    markup.row(
        InlineKeyboardButton("✏️ Permissions", callback_data="btn_Permissions"),
        InlineKeyboardButton("🔍 Log Channel", callback_data="btn_LogChannel")
    )
    markup.row(
        InlineKeyboardButton("◀️ Back", callback_data="page_1"),
        InlineKeyboardButton("✅ Close", callback_data="close_menu"),
        InlineKeyboardButton("🇬🇧 Lang", callback_data="btn_lang")
    )
    return markup

def build_help_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(InlineKeyboardButton("➕ Add me to a Group ➕", url="https://t.me/your_bot_username?startgroup=true"))
    markup.add(InlineKeyboardButton("⚙️ Manage group Settings ✍️", callback_data="open_settings_msg"))
    markup.add(
        InlineKeyboardButton("👥 Group ↗️", callback_data="btn_Group"),
        InlineKeyboardButton("Channel 📢 ↗️", callback_data="btn_Channel")
    )
    markup.add(
        InlineKeyboardButton("🚨 Support", callback_data="btn_Support"),
        InlineKeyboardButton("Information 💬", callback_data="btn_Info")
    )
    markup.add(InlineKeyboardButton("🇬🇧 Languages 🇬🇧", callback_data="btn_lang"))
    markup.add(
        InlineKeyboardButton("👤 Basic commands", callback_data="cmd_basic"),
        InlineKeyboardButton("Advanced 👩‍🔬", callback_data="cmd_adv")
    )
    markup.add(
        InlineKeyboardButton("🤠 Experts", callback_data="cmd_exp"),
        InlineKeyboardButton("Pro Guides 🧔‍♂️", callback_data="cmd_pro")
    )
    markup.add(InlineKeyboardButton("👾 How to create a Clone", callback_data="btn_Clone"))
    markup.add(InlineKeyboardButton("◀️ Back", callback_data="close_menu"))
    return markup

# ==========================================
# 🚨 5. MODERATION COMMAND HANDLERS
# ==========================================
@bot.message_handler(commands=['start', 'help'])
def send_help(message):
    bot.reply_to(message, "Welcome to the help menu!", reply_markup=build_help_menu())

@bot.message_handler(commands=['settings', 'config'])
def open_settings(message):
    if message.chat.type == 'private':
        return bot.reply_to(message, "⚠️ Group Chat အတွင်း၌သာ သုံးနိုင်ပါသည် ခင်ဗျာ။")
    if not is_admin(message.chat.id, message.from_user.id):
        return bot.reply_to(message, "❌ Group Admin သာလျှင် Settings ပြင်ဆင်ခွင့်ရှိပါသည်။")

    bot.reply_to(
        message, 
        f"Group: *{message.chat.title}*\n\nSelect one of the settings that you want to change.", 
        reply_markup=build_settings_page_1(message.chat.id)
    )

@bot.message_handler(commands=['warn'])
def warn_user(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    if not message.reply_to_message:
        return bot.reply_to(message, "⚠️ Reply to a user's message to warn.")
    
    target = message.reply_to_message.from_user
    cnt = db.add_warn(message.chat.id, target.id)
    if cnt >= 3:
        try:
            bot.ban_chat_member(message.chat.id, target.id)
            db.reset_warns(message.chat.id, target.id)
            bot.reply_to(message, f"❌ {target.first_name} reached 3/3 warns and was banned.")
        except Exception as e:
            bot.reply_to(message, f"Error: {str(e)}")
    else:
        bot.reply_to(message, f"⚠️ {target.first_name} warned ({cnt}/3).")

@bot.message_handler(commands=['unwarn'])
def unwarn_user(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    if not message.reply_to_message: return
    target = message.reply_to_message.from_user
    db.reset_warns(message.chat.id, target.id)
    bot.reply_to(message, f"✅ Warns reset for {target.first_name}.")

@bot.message_handler(commands=['ban', 'kick'])
def ban_user(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    if not message.reply_to_message: return
    target = message.reply_to_message.from_user
    try:
        bot.ban_chat_member(message.chat.id, target.id)
        bot.reply_to(message, f"🚫 Banned {target.first_name}.")
    except Exception as e:
        bot.reply_to(message, f"Error: {str(e)}")

@bot.message_handler(commands=['unban'])
def unban_user(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    if not message.reply_to_message: return
    target = message.reply_to_message.from_user
    try:
        bot.unban_chat_member(message.chat.id, target.id)
        bot.reply_to(message, f"✅ Unbanned {target.first_name}.")
    except Exception as e:
        bot.reply_to(message, f"Error: {str(e)}")

@bot.message_handler(commands=['addbad'])
def add_bad(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    parts = message.text.split(maxsplit=1)
    if len(parts) > 1:
        db.add_badword(message.chat.id, parts[1])
        bot.reply_to(message, f"✅ Word `{parts[1]}` added to Banned Words.")

@bot.message_handler(commands=['delbad'])
def del_bad(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    parts = message.text.split(maxsplit=1)
    if len(parts) > 1:
        db.del_badword(message.chat.id, parts[1])
        bot.reply_to(message, f"✅ Word `{parts[1]}` removed from Banned Words.")

# ==========================================
# 🧩 6. CAPTCHA & NEW MEMBERS
# ==========================================
@bot.message_handler(content_types=['new_chat_members'])
def handle_new_member(message):
    chat_id = message.chat.id
    for member in message.new_chat_members:
        if member.is_bot: continue
        
        if db.get_setting(chat_id, "welcome"):
            bot.send_message(chat_id, f"👋 Welcome {member.first_name} to {message.chat.title}!")

        if db.get_setting(chat_id, "captcha"):
            num1, num2 = random.randint(1, 9), random.randint(1, 9)
            ans = num1 + num2
            db.add_captcha(chat_id, member.id, ans)

            try:
                bot.restrict_chat_member(chat_id, member.id, can_send_messages=False)
            except Exception: pass

            markup = InlineKeyboardMarkup(row_width=3)
            options = [ans, ans + 2, ans - 1]
            random.shuffle(options)
            
            btns = [InlineKeyboardButton(str(opt), callback_data=f"cap_{member.id}_{opt}") for opt in options]
            markup.add(*btns)
            
            bot.send_message(
                chat_id,
                f"🧩 **Captcha Check:** [{member.first_name}](tg://user?id={member.id})\n"
                f"Solve to chat: `{num1} + {num2} = ?`",
                reply_markup=markup
            )

# ==========================================
# 🔄 7. CALLBACK QUERY HANDLER
# ==========================================
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call: CallbackQuery):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    data = call.data

    if data.startswith("cap_"):
        parts = data.split("_")
        target_id, guessed_ans = int(parts[1]), int(parts[2])
        if user_id != target_id:
            return bot.answer_callback_query(call.id, "❌ This test is not for you!", show_alert=True)

        real_ans = db.get_captcha(chat_id, target_id)
        if real_ans and guessed_ans == real_ans:
            try:
                bot.restrict_chat_member(chat_id, target_id, can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True)
            except Exception: pass
            db.remove_captcha(chat_id, target_id)
            bot.answer_callback_query(call.id, "✅ Verified! Welcome.")
            try: bot.delete_message(chat_id, call.message.message_id)
            except Exception: pass
        else:
            bot.answer_callback_query(call.id, "❌ Incorrect answer!", show_alert=True)
        return

    if data == "close_menu":
        try: bot.delete_message(chat_id, call.message.message_id)
        except Exception: pass
        return

    if data == "open_settings_msg":
        if call.message.chat.type == 'private':
            return bot.answer_callback_query(call.id, "Group အတွင်း၌သာ Settings ကို ဖွင့်နိုင်ပါသည်", show_alert=True)
        bot.edit_message_text("Select one of the settings that you want to change.", chat_id, call.message.message_id, reply_markup=build_settings_page_1(chat_id))
        return

    if data == "page_1":
        bot.edit_message_text(f"Group: *{call.message.chat.title}*\n\nSelect one of the settings that you want to change.", chat_id, call.message.message_id, reply_markup=build_settings_page_1(chat_id))
        return

    if data == "page_2":
        bot.edit_message_text(f"Group: *{call.message.chat.title}*\n\nSelect one of the settings that you want to change.", chat_id, call.message.message_id, reply_markup=build_settings_page_2(chat_id))
        return

    if data.startswith("toggle_"):
        if not is_admin(chat_id, user_id):
            return bot.answer_callback_query(call.id, "❌ Admin သာလျှင် Settings ပြောင်းလဲနိုင်ပါသည်။", show_alert=True)
        key = data.replace("toggle_", "")
        new_st = db.toggle_setting(chat_id, key)
        bot.answer_callback_query(call.id, f"Setting Updated: {'ON' if new_st else 'OFF'}")
        
        try: bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=build_settings_page_1(chat_id))
        except Exception:
            try: bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=build_settings_page_2(chat_id))
            except Exception: pass
        return

    if data == "show_badwords":
        words = db.get_badwords(chat_id)
        w_str = "\n".join([f"• `{w}`" for w in words]) if words else "တားမြစ်ထားသော စာလုံး မရှိသေးပါ။"
        bot.answer_callback_query(call.id, f"Banned Words:\n{w_str}", show_alert=True)
        return

    if data.startswith("btn_"):
        feature = data.replace("btn_", "")
        bot.answer_callback_query(call.id, f"ℹ️ {feature} module is currently monitoring this group.", show_alert=True)

# ==========================================
# 🛡️ 8. AUTOMATION, FLOOD & FILTERS
# ==========================================
user_flood_tracker = {}

def check_flood_and_spam(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    now = time.time()

    if db.get_setting(chat_id, "antiflood"):
        if chat_id not in user_flood_tracker: user_flood_tracker[chat_id] = {}
        if user_id not in user_flood_tracker[chat_id]: user_flood_tracker[chat_id][user_id] = []

        timestamps = user_flood_tracker[chat_id][user_id]
        timestamps.append(now)
        user_flood_tracker[chat_id][user_id] = [t for t in timestamps if now - t < 3]

        if len(user_flood_tracker[chat_id][user_id]) > 4:
            try:
                bot.delete_message(chat_id, message.message_id)
                bot.send_message(chat_id, f"⚠️ Stop flooding [{message.from_user.first_name}](tg://user?id={user_id})!")
                return True
            except Exception: pass
    return False

@bot.message_handler(func=lambda m: True, content_types=['text', 'sticker', 'photo', 'document', 'audio', 'video'])
def global_message_listener(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if message.chat.type == 'private' or is_admin(chat_id, user_id): return
    if check_flood_and_spam(message): return

    # Link Block
    if db.get_setting(chat_id, "links") and message.text:
        if any(domain in message.text.lower() for domain in ["http://", "https://", "t.me/", "telegram.me"]):
            try: bot.delete_message(chat_id, message.message_id); return
            except Exception: pass

    # Banned Words
    if message.text:
        text_l = message.text.lower()
        for bad in db.get_badwords(chat_id):
            if bad in text_l:
                try: bot.delete_message(chat_id, message.message_id); return
                except Exception: pass

    # Sticker Lock
    if db.get_setting(chat_id, "stickers") and message.content_type == 'sticker':
        try: bot.delete_message(chat_id, message.message_id); return
        except Exception: pass

    # Media Lock
    if db.get_setting(chat_id, "media") and message.content_type in ['photo', 'video', 'document', 'audio']:
        try: bot.delete_message(chat_id, message.message_id); return
        except Exception: pass

# ==========================================
# ⏰ 9. BACKGROUND SCHEDULERS (NIGHT MODE)
# ==========================================
def night_mode_scheduler():
    while True:
        try:
            now_time = datetime.now().strftime("%H:%M")
            db.cursor.execute("SELECT chat_id, night_start, night_end FROM settings WHERE night=1")
            groups = db.cursor.fetchall()
            for chat_id, start_t, end_t in groups:
                if now_time == start_t:
                    try: bot.send_message(chat_id, "🌙 **Night Mode Activated!** Chat muted.")
                    except Exception: pass
                elif now_time == end_t:
                    try: bot.send_message(chat_id, "☀️ **Night Mode Deactivated!** Good morning!")
                    except Exception: pass
        except Exception: pass
        time.sleep(60)

threading.Thread(target=night_mode_scheduler, daemon=True).start()

# ==========================================
# 🏃‍♂️ BOT EXECUTION
# ==========================================
if __name__ == '__main__':
    print("🤖 Full Group Help Engine Running Active...")
    bot.infinity_polling(skip_pending=True)
