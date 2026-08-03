import asyncio

# Fix Python 3.10+ Event Loop Error for Pyrogram on Render
try:
    asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

import os
import re
import time
import json
import threading
import psutil
import psycopg2
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
from pyrogram import Client

# ==========================================
# 🌐 KEEP ALIVE WEB SERVER FOR RENDER
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "All-in-One Management Bot is Running Alive!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_flask, daemon=True).start()

# ==========================================
# 🔑 CREDENTIALS & HARDCODED CONFIG
# ==========================================
BOT_TOKEN = "8886077155:AAET1U9CXGZtaiIBLYxAutzFKFe-BkQpVno"
API_ID = 31788996
API_HASH = "0c6714a879b2b1abba75dc4526521ca8"
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:your_password@db.xxx.supabase.co:5432/postgres")

OWNER_IDS = [7974865879, 7177628115, 8438417346]

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")
userbot = Client("myuserbot", api_id=API_ID, api_hash=API_HASH)

def start_userbot():
    try:
        userbot.start()
        print("✅ Pyrogram Userbot Started Successfully!")
    except Exception as e:
        print(f"❌ Userbot Error: {e}")

threading.Thread(target=start_userbot, daemon=True).start()

mention_cancel_flags = {}
user_message_timestamps = {}

# ==========================================
# 🗄️ DATABASE INITIALIZATION
# ==========================================
def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Tables Setup
        cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id BIGINT PRIMARY KEY, first_name TEXT, username TEXT)')
        cursor.execute('CREATE TABLE IF NOT EXISTS groups (chat_id BIGINT PRIMARY KEY, title TEXT, added_by_id BIGINT, added_by_name TEXT)')
        cursor.execute('CREATE TABLE IF NOT EXISTS sudo_users (user_id BIGINT PRIMARY KEY)')
        cursor.execute('CREATE TABLE IF NOT EXISTS notes (chat_id BIGINT, note_name TEXT, content TEXT, PRIMARY KEY (chat_id, note_name))')
        cursor.execute('CREATE TABLE IF NOT EXISTS filters (chat_id BIGINT, keyword TEXT, reply_text TEXT, PRIMARY KEY (chat_id, keyword))')
        cursor.execute('CREATE TABLE IF NOT EXISTS badwords (chat_id BIGINT, word TEXT, PRIMARY KEY (chat_id, word))')
        cursor.execute('CREATE TABLE IF NOT EXISTS warns (chat_id BIGINT, user_id BIGINT, count INT DEFAULT 0, PRIMARY KEY (chat_id, user_id))')
        cursor.execute('CREATE TABLE IF NOT EXISTS welcomes (chat_id BIGINT PRIMARY KEY, custom_message TEXT, captcha_enabled BOOLEAN DEFAULT FALSE)')
        cursor.execute('CREATE TABLE IF NOT EXISTS rules (chat_id BIGINT PRIMARY KEY, rule_text TEXT)')
        cursor.execute('CREATE TABLE IF NOT EXISTS approved_users (chat_id BIGINT, user_id BIGINT, PRIMARY KEY (chat_id, user_id))')
        cursor.execute('CREATE TABLE IF NOT EXISTS settings (chat_id BIGINT PRIMARY KEY, antiflood_limit INT DEFAULT 5, antiraid BOOLEAN DEFAULT FALSE, clean_service BOOLEAN DEFAULT FALSE, lock_stickers BOOLEAN DEFAULT FALSE, lock_links BOOLEAN DEFAULT FALSE, log_channel BIGINT DEFAULT 0)')
        cursor.execute('CREATE TABLE IF NOT EXISTS federations (fed_id TEXT PRIMARY KEY, fed_name TEXT, owner_id BIGINT)')
        cursor.execute('CREATE TABLE IF NOT EXISTS fed_bans (fed_id TEXT, user_id BIGINT, PRIMARY KEY (fed_id, user_id))')
        
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ Database Initialized Successfully.")
    except Exception as e:
        print(f"❌ DB Init Error: {e}")

try:
    init_db()
except Exception:
    pass

# Helper Functions
def is_owner(user_id):
    return user_id in OWNER_IDS

def is_sudo(user_id):
    if is_owner(user_id):
        return True
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM sudo_users WHERE user_id = %s', (user_id,))
        res = cursor.fetchone()
        cursor.close()
        conn.close()
        return res is not None
    except Exception:
        return False

def is_admin(chat_id, user_id):
    if is_sudo(user_id):
        return True
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ['administrator', 'creator']
    except Exception:
        return False

def save_user(user):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO users (user_id, first_name, username) VALUES (%s, %s, %s) ON CONFLICT (user_id) DO UPDATE SET first_name = EXCLUDED.first_name, username = EXCLUDED.username', (user.id, user.first_name, user.username))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception:
        pass

def save_group(chat_id, title, user_id, user_name):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO groups (chat_id, title, added_by_id, added_by_name) VALUES (%s, %s, %s, %s) ON CONFLICT (chat_id) DO UPDATE SET title = EXCLUDED.title', (chat_id, title, user_id, user_name))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception:
        pass

# ==========================================
# 👑 ADMIN, SUDO & PERMISSIONS MODULE
# ==========================================
@bot.message_handler(commands=['addsudo'])
def cmd_addsudo(message):
    if not is_owner(message.from_user.id): return
    target = message.reply_to_message.from_user.id if message.reply_to_message else int(message.text.split()[1]) if len(message.text.split()) > 1 else None
    if target:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO sudo_users (user_id) VALUES (%s) ON CONFLICT DO NOTHING', (target,))
        conn.commit(); cursor.close(); conn.close()
        bot.reply_to(message, f"✅ User `{target}` ကို Sudo ခွင့်ပြုလိုက်ပါပြီ။")

@bot.message_handler(commands=['rmsudo'])
def cmd_rmsudo(message):
    if not is_owner(message.from_user.id): return
    target = message.reply_to_message.from_user.id if message.reply_to_message else int(message.text.split()[1]) if len(message.text.split()) > 1 else None
    if target:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM sudo_users WHERE user_id = %s', (target,))
        conn.commit(); cursor.close(); conn.close()
        bot.reply_to(message, f"✅ User `{target}` အား Sudo မှ ဖြုတ်လိုက်ပါပြီ။")

@bot.message_handler(commands=['admins', 'adminlist'])
def cmd_admins(message):
    try:
        admins = bot.get_chat_administrators(message.chat.id)
        msg = "👑 **Group Admins စာရင်း:**\n\n"
        for a in admins:
            msg += f"• [{a.user.first_name}](tg://user?id={a.user.id})\n"
        bot.reply_to(message, msg)
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

# ==========================================
# 🚫 BANS, KICKS, MUTE & APPROVAL MODULE
# ==========================================
@bot.message_handler(commands=['ban'])
def cmd_ban(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    if message.reply_to_message:
        bot.ban_chat_member(message.chat.id, message.reply_to_message.from_user.id)
        bot.reply_to(message, f"🚫 User အား Group မှ Ban လိုက်ပါပြီ။")

@bot.message_handler(commands=['unban'])
def cmd_unban(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    if message.reply_to_message:
        bot.unban_chat_member(message.chat.id, message.reply_to_message.from_user.id, only_if_banned=True)
        bot.reply_to(message, f"✅ User အား Unban ပေးလိုက်ပါပြီ။")

@bot.message_handler(commands=['mute'])
def cmd_mute(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    if message.reply_to_message:
        bot.restrict_chat_member(message.chat.id, message.reply_to_message.from_user.id, can_send_messages=False)
        bot.reply_to(message, f"🔇 User ရဲ့ စာရေးခွင့် ပိတ်လိုက်ပါပြီ။")

@bot.message_handler(commands=['unmute'])
def cmd_unmute(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    if message.reply_to_message:
        bot.restrict_chat_member(message.chat.id, message.reply_to_message.from_user.id, can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True)
        bot.reply_to(message, f"🔊 User အား စာပြန်ရေးခွင့် ပေးလိုက်ပါပြီ။")

@bot.message_handler(commands=['approve'])
def cmd_approve(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    if message.reply_to_message:
        target = message.reply_to_message.from_user.id
        conn = get_db_connection(); cursor = conn.cursor()
        cursor.execute('INSERT INTO approved_users (chat_id, user_id) VALUES (%s, %s) ON CONFLICT DO NOTHING', (message.chat.id, target))
        conn.commit(); cursor.close(); conn.close()
        bot.reply_to(message, "✅ User အား Approved စာရင်းသို့ ထည့်သွင်းပြီးပါပြီ။")

# ==========================================
# ⚠️ WARNINGS & ANTIFLOOD SYSTEM
# ==========================================
@bot.message_handler(commands=['warn'])
def cmd_warn(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    if message.reply_to_message:
        target = message.reply_to_message.from_user.id
        conn = get_db_connection(); cursor = conn.cursor()
        cursor.execute('INSERT INTO warns (chat_id, user_id, count) VALUES (%s, %s, 1) ON CONFLICT (chat_id, user_id) DO UPDATE SET count = warns.count + 1 RETURNING count', (message.chat.id, target))
        cnt = cursor.fetchone()[0]
        conn.commit(); cursor.close(); conn.close()
        if cnt >= 3:
            bot.ban_chat_member(message.chat.id, target)
            bot.reply_to(message, f"⚠️ Warn 3 ကြိမ် ပြည့်သွားသဖြင့် Ban လိုက်ပါပြီ။")
        else:
            bot.reply_to(message, f"⚠️ User အား သတိပေးလိုက်ပါပြီ။ (Warn: `{cnt}/3`)")

@bot.message_handler(commands=['setflood'])
def cmd_setflood(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    parts = message.text.split()
    if len(parts) > 1 and parts[1].isdigit():
        limit = int(parts[1])
        conn = get_db_connection(); cursor = conn.cursor()
        cursor.execute('INSERT INTO settings (chat_id, antiflood_limit) VALUES (%s, %s) ON CONFLICT (chat_id) DO UPDATE SET antiflood_limit = EXCLUDED.antiflood_limit', (message.chat.id, limit))
        conn.commit(); cursor.close(); conn.close()
        bot.reply_to(message, f"⚡ Antiflood Limit ကို `{limit}` ဟု သတ်မှတ်လိုက်ပါပြီ။")

# ==========================================
# 📝 NOTES, FILTERS & BADWORDS MODULE
# ==========================================
@bot.message_handler(commands=['save'])
def cmd_save_note(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    parts = message.text.split(maxsplit=2)
    if len(parts) >= 3:
        conn = get_db_connection(); cursor = conn.cursor()
        cursor.execute('INSERT INTO notes (chat_id, note_name, content) VALUES (%s, %s, %s) ON CONFLICT (chat_id, note_name) DO UPDATE SET content = EXCLUDED.content', (message.chat.id, parts[1].lower(), parts[2]))
        conn.commit(); cursor.close(); conn.close()
        bot.reply_to(message, f"📝 Note `#{parts[1]}` အား မှတ်သားလိုက်ပါပြီ။")

@bot.message_handler(commands=['filter'])
def cmd_add_filter(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    parts = message.text.split(maxsplit=2)
    if len(parts) >= 3:
        conn = get_db_connection(); cursor = conn.cursor()
        cursor.execute('INSERT INTO filters (chat_id, keyword, reply_text) VALUES (%s, %s, %s) ON CONFLICT (chat_id, keyword) DO UPDATE SET reply_text = EXCLUDED.reply_text', (message.chat.id, parts[1].lower(), parts[2]))
        conn.commit(); cursor.close(); conn.close()
        bot.reply_to(message, f"🎯 Filter `{parts[1]}` ထည့်သွင်းလိုက်ပါပြီ။")

@bot.message_handler(commands=['addbad'])
def cmd_addbad(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    parts = message.text.split(maxsplit=1)
    if len(parts) >= 2:
        conn = get_db_connection(); cursor = conn.cursor()
        cursor.execute('INSERT INTO badwords (chat_id, word) VALUES (%s, %s) ON CONFLICT DO NOTHING', (message.chat.id, parts[1].lower()))
        conn.commit(); cursor.close(); conn.close()
        bot.reply_to(message, f"🚫 Badword `{parts[1]}` အား သတ်မှတ်လိုက်ပါပြီ။")

# ==========================================
# 📢 TAG ALL / TAG ADMINS MODULE
# ==========================================
def run_mention_all(chat_id, text_to_send, sender_name):
    mention_cancel_flags[chat_id] = False
    try:
        members = list(userbot.get_chat_members(chat_id))
        bot.send_message(chat_id, f"📢 **{sender_name}** မှ Tag ခေါ်ခြင်း စတင်ပါပြီ...\nရပ်တန့်ရန်: `/stopmention` သို့မဟုတ် `/cancel`")
        
        batch = []
        for m in members:
            if mention_cancel_flags.get(chat_id, False):
                bot.send_message(chat_id, "🛑 Tag ခေါ်ခြင်းကို ရပ်တန့်လိုက်ပါပြီ။")
                return

            if not m.user.is_bot:
                clean_name = m.user.first_name.replace("[", "").replace("]", "") if m.user.first_name else "User"
                batch.append(f"[{clean_name}](tg://user?id={m.user.id})")
                
                if len(batch) == 5:
                    bot.send_message(chat_id, f"📢 **{text_to_send}**\n\n" + " ".join(batch))
                    batch = []
                    time.sleep(2)
        
        if batch and not mention_cancel_flags.get(chat_id, False):
            bot.send_message(chat_id, f"📢 **{text_to_send}**\n\n" + " ".join(batch))
            
    except Exception as e:
        bot.send_message(chat_id, f"❌ Tag Error: `{e}`")

@bot.message_handler(commands=['all', 'tagall'])
def cmd_tagall(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    text = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else "မင်္ဂလာပါ လူကြီးမင်းတို့ ခင်ဗျာ!"
    threading.Thread(target=run_mention_all, args=(message.chat.id, text, message.from_user.first_name)).start()

@bot.message_handler(commands=['stopmention', 'cancel'])
def cmd_stopmention(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    mention_cancel_flags[message.chat.id] = True
    bot.reply_to(message, "🛑 Mention Tag ခေါ်ခြင်းကို ရပ်တန့်လိုက်ပါပြီ။")

# ==========================================
# 🧹 PURGE, PIN & RULES MODULE
# ==========================================
@bot.message_handler(commands=['purge'])
def cmd_purge(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    if not message.reply_to_message:
        return bot.reply_to(message, "⚠️ Purging စလုပ်ချင်သည့် Message ကို Reply ပြန်ပေးပါ။")
    
    start_id = message.reply_to_message.message_id
    end_id = message.message_id
    deleted = 0
    for msg_id in range(start_id, end_id + 1):
        try:
            bot.delete_message(message.chat.id, msg_id)
            deleted += 1
        except Exception:
            pass
    msg = bot.send_message(message.chat.id, f"🧹 Message ပေါင်း `{deleted}` ခုအား Auto ဖျက်ပြီးပါပြီ။")
    time.sleep(3)
    try: bot.delete_message(message.chat.id, msg.message_id)
    except Exception: pass

@bot.message_handler(commands=['pin'])
def cmd_pin(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    if message.reply_to_message:
        bot.pin_chat_message(message.chat.id, message.reply_to_message.message_id)
        bot.reply_to(message, "📌 Message ကို Pin ချိတ်လိုက်ပါပြီ။")

@bot.message_handler(commands=['setrules'])
def cmd_setrules(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    parts = message.text.split(maxsplit=1)
    if len(parts) > 1:
        conn = get_db_connection(); cursor = conn.cursor()
        cursor.execute('INSERT INTO rules (chat_id, rule_text) VALUES (%s, %s) ON CONFLICT (chat_id) DO UPDATE SET rule_text = EXCLUDED.rule_text', (message.chat.id, parts[1]))
        conn.commit(); cursor.close(); conn.close()
        bot.reply_to(message, "📜 Group Rules သတ်မှတ်လိုက်ပါပြီ။")

@bot.message_handler(commands=['rules'])
def cmd_rules(message):
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute('SELECT rule_text FROM rules WHERE chat_id = %s', (message.chat.id,))
    row = cursor.fetchone()
    cursor.close(); conn.close()
    if row:
        bot.reply_to(message, f"📜 **Group Rules:**\n\n{row[0]}")
    else:
        bot.reply_to(message, "ℹ️ Rules မသတ်မှတ်ရသေးပါ။")

# ==========================================
# 📢 BROADCAST & STATS MODULE
# ==========================================
@bot.message_handler(commands=['broadcast'])
def cmd_broadcast(message):
    if not is_sudo(message.from_user.id): return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2: return
    text = parts[1]
    
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users')
    users = cursor.fetchall()
    cursor.execute('SELECT chat_id FROM groups')
    groups = cursor.fetchall()
    cursor.close(); conn.close()

    bot.reply_to(message, "📢 Broadcast Message စတင် ပို့ဆောင်နေပါပြီ...")
    u_success, g_success = 0, 0
    for u in users:
        try:
            bot.send_message(u[0], f"📢 **Broadcast:**\n\n{text}")
            u_success += 1
            time.sleep(0.05)
        except Exception: pass
        
    for g in groups:
        try:
            bot.send_message(g[0], f"📢 **Broadcast:**\n\n{text}")
            g_success += 1
            time.sleep(0.05)
        except Exception: pass

    bot.reply_to(message, f"✅ Broadcast ပို့ပြီးပါပြီ!\n\n👤 Users: `{u_success}`\n👥 Groups: `{g_success}`")

# ==========================================
# 🔘 HELP & ALL-IN-ONE LISTENER
# ==========================================
def get_main_help_markup():
    markup = InlineKeyboardMarkup(row_width=3)
    buttons = [
        InlineKeyboardButton("👑 Admin/Sudo", callback_data="help_admin"),
        InlineKeyboardButton("📢 Mention/Tag", callback_data="help_mention"),
        InlineKeyboardButton("🚫 Bans/Mute", callback_data="help_bans"),
        InlineKeyboardButton("⚠️ Warnings", callback_data="help_warns"),
        InlineKeyboardButton("📝 Notes/Filters", callback_data="help_notes"),
        InlineKeyboardButton("📜 Rules/Purge", callback_data="help_rules"),
        InlineKeyboardButton("📢 Broadcast", callback_data="help_broadcast")
    ]
    markup.add(*buttons)
    return markup

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    save_user(message.from_user)
    if message.chat.type in ['group', 'supergroup']:
        save_group(message.chat.id, message.chat.title, message.from_user.id, message.from_user.first_name)
    bot.reply_to(message, "👋 မင်္ဂလာပါ! Group Management Bot အပြည့်အစုံမှ ကြိုဆိုပါတယ်။\nအောက်ပါ အမိန့်များကို သုံးနိုင်ပါသည် -", reply_markup=get_main_help_markup())

@bot.message_handler(func=lambda m: True, content_types=['text', 'sticker', 'new_chat_members', 'left_chat_member'])
def main_listener(message):
    if message.chat.type in ['group', 'supergroup']:
        save_group(message.chat.id, message.chat.title, message.from_user.id, message.from_user.first_name)
    save_user(message.from_user)

    # Clean Service Messages (Joined/Left Group Messages)
    if message.content_type in ['new_chat_members', 'left_chat_member']:
        try: bot.delete_message(message.chat.id, message.message_id)
        except Exception: pass
        return

    # Auto Filters Listener
    if message.text:
        conn = get_db_connection(); cursor = conn.cursor()
        cursor.execute('SELECT reply_text FROM filters WHERE chat_id = %s AND keyword = %s', (message.chat.id, message.text.lower()))
        row = cursor.fetchone()
        
        # Check Badwords
        cursor.execute('SELECT word FROM badwords WHERE chat_id = %s', (message.chat.id,))
        bwords = [r[0] for r in cursor.fetchall()]
        cursor.close(); conn.close()

        if row:
            bot.reply_to(message, row[0])

        for bw in bwords:
            if bw in message.text.lower():
                try:
                    bot.delete_message(message.chat.id, message.message_id)
                    bot.send_message(message.chat.id, f"⚠️ [{message.from_user.first_name}](tg://user?id={message.from_user.id}) မကောင်းသော စာလုံးများ သုံးခွင့်မရှိပါ။")
                except Exception: pass
                break

if __name__ == '__main__':
    print("🤖 Bot is successfully running with ZERO errors!")
    bot.infinity_polling()
