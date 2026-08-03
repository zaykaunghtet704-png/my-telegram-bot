import os
import time
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
    return "Bot is running alive!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()

keep_alive()

# ==========================================
# 🔑 CREDENTIALS & CONFIGURATION
# ==========================================
BOT_TOKEN = "8886077155:AAET1U9CXGZtaiIBLYxAutzFKFe-BkQpVno"
API_ID = 31788996
API_HASH = "0c6714a879b2b1abba75dc4526521ca8"

# Supabase Database URL ကို Render Environment မှ ယူမည် သို့မဟုတ် ဤနေရာတွင် direct ထည့်နိုင်သည်
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:your_password@db.xxx.supabase.co:5432/postgres")

OWNER_IDS = [7974865879, 7177628115, 8438417346]

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

# Pyrogram Userbot Client Setup
userbot = Client("myuserbot", api_id=API_ID, api_hash=API_HASH)

def start_userbot():
    try:
        userbot.start()
        print("✅ Pyrogram Userbot Successfully Started!")
    except Exception as e:
        print(f"❌ Userbot Start Error: {e}")

threading.Thread(target=start_userbot, daemon=True).start()

mention_cancel_flags = {}

# ==========================================
# 🗄️ DATABASE SETUP
# ==========================================
def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id BIGINT PRIMARY KEY, first_name TEXT, username TEXT)')
        cursor.execute('CREATE TABLE IF NOT EXISTS groups (chat_id BIGINT PRIMARY KEY, title TEXT, added_by_id BIGINT, added_by_name TEXT)')
        cursor.execute('CREATE TABLE IF NOT EXISTS notes (chat_id BIGINT, note_name TEXT, content TEXT, PRIMARY KEY (chat_id, note_name))')
        cursor.execute('CREATE TABLE IF NOT EXISTS warns (chat_id BIGINT, user_id BIGINT, count INT DEFAULT 0, PRIMARY KEY (chat_id, user_id))')
        cursor.execute('CREATE TABLE IF NOT EXISTS welcomes (chat_id BIGINT PRIMARY KEY, custom_message TEXT)')
        cursor.execute('CREATE TABLE IF NOT EXISTS filters (chat_id BIGINT, keyword TEXT, reply_text TEXT, PRIMARY KEY (chat_id, keyword))')
        cursor.execute('CREATE TABLE IF NOT EXISTS badwords (chat_id BIGINT, word TEXT, PRIMARY KEY (chat_id, word))')
        cursor.execute('CREATE TABLE IF NOT EXISTS sudo_users (user_id BIGINT PRIMARY KEY)')
        cursor.execute('CREATE TABLE IF NOT EXISTS rules (chat_id BIGINT PRIMARY KEY, rule_text TEXT)')
        cursor.execute('CREATE TABLE IF NOT EXISTS locks (chat_id BIGINT PRIMARY KEY, lock_stickers BOOLEAN DEFAULT FALSE, lock_links BOOLEAN DEFAULT FALSE)')
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ Database initialized successfully.")
    except Exception as e:
        print(f"❌ DB Init Error: {e}")

try:
    init_db()
except Exception:
    pass

# Helper Functions
def is_owner(user_id):
    return user_id in OWNER_IDS

def is_authorized(user_id):
    if user_id in OWNER_IDS:
        return True
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM sudo_users WHERE user_id = %s', (user_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return row is not None
    except Exception:
        return False

def save_user(user):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (user_id, first_name, username)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE 
            SET first_name = EXCLUDED.first_name, username = EXCLUDED.username
        ''', (user.id, user.first_name, user.username))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception:
        pass

def save_group(chat_id, title, added_by_id, added_by_name):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO groups (chat_id, title, added_by_id, added_by_name)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (chat_id) DO UPDATE 
            SET title = EXCLUDED.title, added_by_id = EXCLUDED.added_by_id, added_by_name = EXCLUDED.added_by_name
        ''', (chat_id, title, added_by_id, added_by_name))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception:
        pass

# ==========================================
# 👑 ADMIN & SUDO COMMANDS
# ==========================================
@bot.message_handler(commands=['addsudo'])
def cmd_addsudo(message):
    if not is_owner(message.from_user.id):
        return bot.reply_to(message, "❌ Owner သာလျှင် Sudo ထည့်သွင်းနိုင်ပါသည်။")
    
    target_id = None
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
    else:
        parts = message.text.split()
        if len(parts) > 1 and parts[1].isdigit():
            target_id = int(parts[1])

    if not target_id:
        return bot.reply_to(message, "⚠️ Sudo ထည့်လိုသော User ကို Reply ပြန်ပါ သို့မဟုတ် ID ရိုက်ထည့်ပါ (ဥပမာ: `/addsudo 12345678`)")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO sudo_users (user_id) VALUES (%s) ON CONFLICT DO NOTHING', (target_id,))
        conn.commit()
        cursor.close()
        conn.close()
        bot.reply_to(message, f"✅ User `{target_id}` အား Sudo User အဖြစ် ထည့်သွင်းလိုက်ပါပြီ။")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

@bot.message_handler(commands=['rmsudo'])
def cmd_rmsudo(message):
    if not is_owner(message.from_user.id):
        return bot.reply_to(message, "❌ Owner သာလျှင် Sudo ဖြုတ်နိုင်ပါသည်။")
    
    target_id = None
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
    else:
        parts = message.text.split()
        if len(parts) > 1 and parts[1].isdigit():
            target_id = int(parts[1])

    if not target_id:
        return bot.reply_to(message, "⚠️ Sudo ဖြုတ်လိုသော User ကို Reply ပြန်ပါ သို့မဟုတ် ID ရိုက်ထည့်ပါ။")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM sudo_users WHERE user_id = %s', (target_id,))
        conn.commit()
        cursor.close()
        conn.close()
        bot.reply_to(message, f"✅ User `{target_id}` အား Sudo စာရင်းမှ ဖြုတ်လိုက်ပါပြီ။")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

# ==========================================
# 🔨 MODERATION (BAN, UNBAN, KICK, MUTE)
# ==========================================
@bot.message_handler(commands=['ban'])
def cmd_ban(message):
    if not is_authorized(message.from_user.id):
        return bot.reply_to(message, "❌ ခွင့်ပြုချက်မရှိပါ။")
    if not message.reply_to_message:
        return bot.reply_to(message, "⚠️ Ban ချင်သော Member ၏ Message ကို Reply ပြန်ပါ။")
    
    target = message.reply_to_message.from_user
    try:
        bot.ban_chat_member(message.chat.id, target.id)
        bot.reply_to(message, f"🚫 [{target.first_name}](tg://user?id={target.id}) အား Group မှ Ban လိုက်ပါပြီ။")
    except Exception as e:
        bot.reply_to(message, f"❌ Ban ရာတွင် Error တက်ပါသည်: {e}")

@bot.message_handler(commands=['unban'])
def cmd_unban(message):
    if not is_authorized(message.from_user.id):
        return bot.reply_to(message, "❌ ခွင့်ပြုချက်မရှိပါ။")
    if not message.reply_to_message:
        return bot.reply_to(message, "⚠️ Unban ပေးချင်သော Member ကို Reply ပြန်ပါ။")
    
    target = message.reply_to_message.from_user
    try:
        bot.unban_chat_member(message.chat.id, target.id, only_if_banned=True)
        bot.reply_to(message, f"✅ [{target.first_name}](tg://user?id={target.id}) အား Unban ပေးလိုက်ပါပြီ။")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

@bot.message_handler(commands=['mute'])
def cmd_mute(message):
    if not is_authorized(message.from_user.id):
        return bot.reply_to(message, "❌ ခွင့်ပြုချက်မရှိပါ။")
    if not message.reply_to_message:
        return bot.reply_to(message, "⚠️ Mute ပိတ်ချင်သော Member ကို Reply ပြန်ပါ။")
    
    target = message.reply_to_message.from_user
    try:
        bot.restrict_chat_member(message.chat.id, target.id, can_send_messages=False)
        bot.reply_to(message, f"🔇 [{target.first_name}](tg://user?id={target.id}) ရဲ့ စာရေးခွင့်ကို ပိတ်လိုက်ပါပြီ။")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

@bot.message_handler(commands=['unmute'])
def cmd_unmute(message):
    if not is_authorized(message.from_user.id):
        return bot.reply_to(message, "❌ ခွင့်ပြုချက်မရှိပါ။")
    if not message.reply_to_message:
        return bot.reply_to(message, "⚠️ Unmute ပေးချင်သော Member ကို Reply ပြန်ပါ။")
    
    target = message.reply_to_message.from_user
    try:
        bot.restrict_chat_member(message.chat.id, target.id, can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True)
        bot.reply_to(message, f"🔊 [{target.first_name}](tg://user?id={target.id}) အား စာပြန်ရေးခွင့် ပေးလိုက်ပါပြီ။")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

# ==========================================
# ⚠️ WARNING SYSTEM
# ==========================================
@bot.message_handler(commands=['warn'])
def cmd_warn(message):
    if not is_authorized(message.from_user.id):
        return bot.reply_to(message, "❌ ခွင့်ပြုချက်မရှိပါ။")
    if not message.reply_to_message:
        return bot.reply_to(message, "⚠️ Warn ပေးချင်သော Member ကို Reply ပြန်ပါ။")
    
    target = message.reply_to_message.from_user
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO warns (chat_id, user_id, count) VALUES (%s, %s, 1) ON CONFLICT (chat_id, user_id) DO UPDATE SET count = warns.count + 1 RETURNING count', (message.chat.id, target.id))
        warn_count = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()

        if warn_count >= 3:
            bot.ban_chat_member(message.chat.id, target.id)
            bot.reply_to(message, f"⚠️ [{target.first_name}](tg://user?id={target.id}) သည် Warn 3 ကြိမ် ပြည့်သွားသဖြင့် Auto Ban ခဲ့ပါသည်။")
        else:
            bot.reply_to(message, f"⚠️ [{target.first_name}](tg://user?id={target.id}) အား သတိပေးလိုက်ပါပြီ။ (Warn Count: `{warn_count}/3`)")
    except Exception as e:
        bot.reply_to(message, f"❌ Warn Error: {e}")

# ==========================================
# 📝 NOTES & FILTERS SYSTEM
# ==========================================
@bot.message_handler(commands=['save'])
def cmd_save_note(message):
    if not is_authorized(message.from_user.id):
        return bot.reply_to(message, "❌ ခွင့်ပြုချက်မရှိပါ။")
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        return bot.reply_to(message, "⚠️ သုံးနည်း: `/save [notename] [content]`")
    
    note_name = parts[1].lower()
    content = parts[2]

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO notes (chat_id, note_name, content) VALUES (%s, %s, %s) ON CONFLICT (chat_id, note_name) DO UPDATE SET content = EXCLUDED.content', (message.chat.id, note_name, content))
        conn.commit()
        cursor.close()
        conn.close()
        bot.reply_to(message, f"✅ Note `#{note_name}` အား မှတ်သားလိုက်ပါပြီ။")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

@bot.message_handler(commands=['filter'])
def cmd_add_filter(message):
    if not is_authorized(message.from_user.id):
        return bot.reply_to(message, "❌ ခွင့်ပြုချက်မရှိပါ။")
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        return bot.reply_to(message, "⚠️ သုံးနည်း: `/filter [keyword] [reply text]`")
    
    keyword = parts[1].lower()
    reply_text = parts[2]

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO filters (chat_id, keyword, reply_text) VALUES (%s, %s, %s) ON CONFLICT (chat_id, keyword) DO UPDATE SET reply_text = EXCLUDED.reply_text', (message.chat.id, keyword, reply_text))
        conn.commit()
        cursor.close()
        conn.close()
        bot.reply_to(message, f"🎯 Auto Filter `{keyword}` အား ထည့်သွင်းလိုက်ပါပြီ။")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

# ==========================================
# 📢 BROADCAST & GHOSTS SYSTEM
# ==========================================
@bot.message_handler(commands=['broadcast'])
def cmd_broadcast(message):
    if not is_authorized(message.from_user.id):
        return bot.reply_to(message, "❌ ခွင့်ပြုချက်မရှိပါ။")
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return bot.reply_to(message, "⚠️ သုံးနည်း: `/broadcast [ပို့ချင်သော စာသား]`")

    text = parts[1]
    bot.reply_to(message, "📢 Broadcast စာပို့ခြင်း စတင်ပါပြီ...")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users')
        users = cursor.fetchall()
        cursor.execute('SELECT chat_id FROM groups')
        groups = cursor.fetchall()
        cursor.close()
        conn.close()

        success_u, success_g = 0, 0
        for u in users:
            try:
                bot.send_message(u[0], f"📢 **Broadcast Message:**\n\n{text}")
                success_u += 1
                time.sleep(0.1)
            except Exception:
                pass

        for g in groups:
            try:
                bot.send_message(g[0], f"📢 **Broadcast Message:**\n\n{text}")
                success_g += 1
                time.sleep(0.1)
            except Exception:
                pass

        bot.reply_to(message, f"✅ Broadcast ပို့ပြီးပါပြီ!\n\n👤 Users: `{success_u}`\n👥 Groups: `{success_g}`")
    except Exception as e:
        bot.reply_to(message, f"❌ Broadcast Error: {e}")

# ==========================================
# 🔘 START, HELP & CALLBACK
# ==========================================
def get_main_help_markup():
    markup = InlineKeyboardMarkup(row_width=3)
    buttons = [
        InlineKeyboardButton("👑 Admin/Sudo", callback_data="help_admin"),
        InlineKeyboardButton("📢 Mention/Tag", callback_data="help_mention"),
        InlineKeyboardButton("🔒 Locks", callback_data="help_locks"),
        InlineKeyboardButton("🚫 Bans/Mute", callback_data="help_bans"),
        InlineKeyboardButton("⚠️ Warnings", callback_data="help_warns"),
        InlineKeyboardButton("🎯 Auto Filters", callback_data="help_filters"),
        InlineKeyboardButton("📝 Notes", callback_data="help_notes"),
        InlineKeyboardButton("📜 Rules", callback_data="help_rules"),
        InlineKeyboardButton("🧹 Purges/Clean", callback_data="help_purges"),
        InlineKeyboardButton("📢 Broadcast/Stats", callback_data="help_broadcast")
    ]
    markup.add(*buttons)
    return markup

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    save_user(message.from_user)
    if message.chat.type in ['group', 'supergroup']:
        save_group(message.chat.id, message.chat.title, message.from_user.id, message.from_user.first_name)
    bot.reply_to(
        message, 
        "👋 မင်္ဂလာပါ! Rose Bot နှင့် Mention Tag Bot တို့၏ Features များအစုံပါဝင်သော Group Management Bot မှ ကြိုဆိုပါတယ်။", 
        reply_markup=get_main_help_markup()
    )

@bot.message_handler(func=lambda m: True, content_types=['text', 'sticker'])
def handle_all_messages(message):
    if message.chat.type in ['group', 'supergroup']:
        save_group(message.chat.id, message.chat.title, message.from_user.id, message.from_user.first_name)
    save_user(message.from_user)

if __name__ == '__main__':
    print("🤖 Bot is starting polling...")
    bot.infinity_polling()
