import asyncio
# Python 3.10+ / 3.14+ MainThread Event Loop Fix for Pyrogram
try:
    asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

import os
import re
import time
import threading
import platform
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
# CONFIGURATION
# ==========================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8886077155:AAET1U9CXGZtaiIBLYxAutzFKFe-BkQpVno")
API_ID = int(os.environ.get("API_ID", 31788996))
API_HASH = os.environ.get("API_HASH", "0c6714a879b2b1abba75dc4526521ca8")
OWNER_IDS = [7974865879, 7177628115, 8438417346]
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres.fdfcifwziqrqqjimtqgm:zaykaunghtet704%23%40@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres")

bot = telebot.TeleBot(BOT_TOKEN)

# Mention ရပ်ရန် Tracking Dict
mention_cancel_flags = {}

# ==========================================
# SUPABASE DATABASE SETUP & HELPERS
# ==========================================
def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                first_name TEXT,
                username TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS groups (
                chat_id BIGINT PRIMARY KEY,
                title TEXT,
                added_by_id BIGINT,
                added_by_name TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notes (
                chat_id BIGINT,
                note_name TEXT,
                content TEXT,
                PRIMARY KEY (chat_id, note_name)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS warns (
                chat_id BIGINT,
                user_id BIGINT,
                count INT DEFAULT 0,
                PRIMARY KEY (chat_id, user_id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS welcomes (
                chat_id BIGINT PRIMARY KEY,
                custom_message TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS filters (
                chat_id BIGINT,
                keyword TEXT,
                reply_text TEXT,
                PRIMARY KEY (chat_id, keyword)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS badwords (
                chat_id BIGINT,
                word TEXT,
                PRIMARY KEY (chat_id, word)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sudo_users (
                user_id BIGINT PRIMARY KEY
            )
        ''')
        conn.commit()
        cursor.close()
        conn.close()
        print("Database initialized successfully.")
    except Exception as e:
        print(f"DB Init Error: {e}")

init_db()

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
    except Exception as e:
        print(f"Error saving user: {e}")

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
    except Exception as e:
        print(f"Error saving group: {e}")

def get_rose_help_markup():
    markup = InlineKeyboardMarkup(row_width=3)
    buttons = [
        InlineKeyboardButton("👑 Admin/Sudo", callback_data="help_admin"),
        InlineKeyboardButton("📢 Tag/Mention", callback_data="help_mention"),
        InlineKeyboardButton("🚫 Badwords", callback_data="help_badwords"),
        InlineKeyboardButton("🎯 Filters", callback_data="help_filters"),
        InlineKeyboardButton("📝 Notes", callback_data="help_notes"),
        InlineKeyboardButton("⚠️ Warnings", callback_data="help_warns"),
        InlineKeyboardButton("👋 Welcome", callback_data="help_welcome"),
        InlineKeyboardButton("🛡 Anti-Link", callback_data="help_antilink"),
        InlineKeyboardButton("📌 Pin", callback_data="help_pin"),
        InlineKeyboardButton("🔇 Mute", callback_data="help_mute"),
        InlineKeyboardButton("🚫 Ban/Kick", callback_data="help_ban"),
        InlineKeyboardButton("📢 Broadcast", callback_data="help_broadcast")
    ]
    markup.add(*buttons)
    return markup

LINK_PATTERN = re.compile(
    r'('
    r'https?://[^\s]+'
    r'|www\.[^\s]+'
    r'|t\.me/(?:\+|\bjoinchat\b|[a-zA-Z0-9_]+)'
    r'|telegram\.me/[a-zA-Z0-9_]+'
    r'|[a-zA-Z0-9.-]+\.(com|net|org|me|io|co|app|xyz|site|online|link|info|live|store|biz|mobi)\b'
    r'|@[a-zA-Z0-9_]{4,}'
    r')',
    re.IGNORECASE
)

def contains_link(text):
    if not text:
        return False
    return bool(LINK_PATTERN.search(text))

# ==========================================
# BASIC COMMANDS & SYSTEM STATUS
# ==========================================
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "👋 မင်္ဂလာပါ! Group Control Bot မှ ကြိုဆိုပါတယ်။ အောက်ပါ Button များကို နှိပ်၍ အမိန့်များကို ကြည့်နိုင်ပါသည်။", reply_markup=get_rose_help_markup())

@bot.message_handler(commands=['status', 'system'])
def cmd_status(message):
    try:
        # CPU Info
        cpu_usage = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()

        # RAM Info
        ram = psutil.virtual_memory()
        ram_total = round(ram.total / (1024 ** 3), 2)  # GB
        ram_used = round(ram.used / (1024 ** 3), 2)   # GB
        ram_percent = ram.percent

        # Disk Info
        disk = psutil.disk_usage('/')
        disk_total = round(disk.total / (1024 ** 3), 2) # GB
        disk_used = round(disk.used / (1024 ** 3), 2)   # GB
        disk_percent = disk.percent

        # System OS
        system_os = platform.system()

        status_msg = (
            "📊 **Bot System Status & Performance**\n\n"
            f"🖥 **OS:** `{system_os}`\n"
            f"⚡ **CPU Usage:** `{cpu_usage}%` ({cpu_count} Cores)\n"
            f"🧠 **RAM Usage:** `{ram_used} GB / {ram_total} GB` (`{ram_percent}%`)\n"
            f"💾 **Disk Storage:** `{disk_used} GB / {disk_total} GB` (`{disk_percent}%`)\n\n"
            "✅ **Bot Status:** Online (အလုပ်လုပ်နေပါသည်)"
        )

        bot.reply_to(message, status_msg, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ Status စစ်ဆေးရာတွင် Error တက်နေပါသည်: {e}")

# ==========================================
# 📢 REAL ALL MEMBERS MENTION (PYROGRAM)
# ==========================================
async def async_fetch_and_mention(chat_id, text_to_send):
    mention_cancel_flags[chat_id] = False
    members = []
    
    # Safe Pyrogram Client Start Inside Async Event Loop
    async_pyro = Client("tg_bot_pyro", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)
    try:
        await async_pyro.start()
        async for member in async_pyro.get_chat_members(chat_id):
            if not member.user.is_bot:
                members.append(member.user)
        await async_pyro.stop()
    except Exception as e:
        print(f"Pyrogram Fetch Error: {e}")

    if not members:
        bot.send_message(chat_id, "ℹ️ Group ထဲတွင် Member စာရင်း ဆွဲထုတ်၍ မရပါ သို့မဟုတ် Member မရှိပါ။")
        return

    bot.send_message(chat_id, f"📢 စုစုပေါင်း Member (`{len(members)}`) ယောက်အား Mention ခေါ်ယူခြင်း စတင်ပါပြီ...", parse_mode="Markdown")

    chunk_size = 5
    for i in range(0, len(members), chunk_size):
        if mention_cancel_flags.get(chat_id, False):
            bot.send_message(chat_id, "🛑 Mention ခေါ်ယူခြင်းကို ရပ်တန့်လိုက်ပါပြီ။")
            break

        chunk = members[i:i + chunk_size]
        mentions = [f"[{m.first_name}](tg://user?id={m.id})" for m in chunk]
        msg = f"📢 **{text_to_send}**\n\n" + " ".join(mentions)
        
        try:
            bot.send_message(chat_id, msg, parse_mode="Markdown")
        except Exception:
            pass
        time.sleep(2.5)

def run_async_mention_thread(chat_id, text_to_send):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(async_fetch_and_mention(chat_id, text_to_send))
    loop.close()

@bot.message_handler(commands=['all', 'tagall'])
def cmd_tag_all(message):
    if not is_authorized(message.from_user.id):
        bot.reply_to(message, "❌ ဤ Command ကို **Authorized User** များသာ သုံးနိုင်ပါသည်။")
        return
    parts = message.text.split(maxsplit=1)
    text_to_send = parts[1] if len(parts) > 1 else "အဖွဲ့ဝင်များအားလုံး သတိထားရန်!"

    threading.Thread(target=run_async_mention_thread, args=(message.chat.id, text_to_send)).start()

@bot.message_handler(commands=['admins', 'admin'])
def cmd_tag_admins(message):
    if message.chat.type not in ['group', 'supergroup']:
        return

    parts = message.text.split(maxsplit=1)
    custom_text = parts[1] if len(parts) > 1 else "Admins များ သတိထားရန်!"

    try:
        admins = bot.get_chat_administrators(message.chat.id)
        admin_mentions = []
        for admin in admins:
            if not admin.user.is_bot:
                admin_mentions.append(f"[{admin.user.first_name}](tg://user?id={admin.user.id})")

        msg = f"👑 **{custom_text}**\n\n" + " ".join(admin_mentions)
        bot.send_message(message.chat.id, msg, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

@bot.message_handler(commands=['cancelmention', 'stopmention'])
def cmd_cancel_mention(message):
    if not is_authorized(message.from_user.id):
        bot.reply_to(message, "❌ ဤ Command ကို **Authorized User** များသာ သုံးနိုင်ပါသည်။")
        return
    mention_cancel_flags[message.chat.id] = True
    bot.reply_to(message, "🛑 Mention ခေါ်ခြင်းကို ရပ်တန့်ရန် အချက်ပြလိုက်ပါပြီ။")

# ==========================================
# ALL MESSAGES HANDLER
# ==========================================
@bot.message_handler(func=lambda message: True, content_types=['text', 'photo', 'video', 'document', 'animation'])
def handle_all_messages(message):
    text = message.text or message.caption or ""

    if message.chat.type == 'private':
        save_user(message.from_user)

    elif message.chat.type in ['group', 'supergroup']:
        save_group(message.chat.id, message.chat.title, message.from_user.id, message.from_user.first_name)
        
        if text.strip() == "@all" and is_authorized(message.from_user.id):
            threading.Thread(target=run_async_mention_thread, args=(message.chat.id, "အဖွဲ့ဝင်များအားလုံး သတိထားရန်!")).start()
            return
        elif text.strip() == "@admins":
            cmd_tag_admins(message)
            return

# ==========================================
# START BOT
# ==========================================
if __name__ == "__main__":
    print("Starting Telegram Bot...")
    bot.infinity_polling(skip_pending=True)
