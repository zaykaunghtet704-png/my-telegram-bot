import asyncio
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
OWNER_IDS = [7974865879, 7177628115, 8438417346]
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres.fdfcifwziqrqqjimtqgm:zaykaunghtet704%23%40@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

mention_cancel_flags = {}

# ==========================================
# DATABASE SETUP & HELPERS
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
        InlineKeyboardButton("📌 Pin", callback_data="help_pin"),
        InlineKeyboardButton("🔇 Mute", callback_data="help_mute"),
        InlineKeyboardButton("🚫 Ban/Kick", callback_data="help_ban"),
        InlineKeyboardButton("📢 Broadcast", callback_data="help_broadcast")
    ]
    markup.add(*buttons)
    return markup

# ==========================================
# 🔘 HELP CALLBACK HANDLERS (WITH WORKING BACK BUTTON)
# ==========================================
@bot.callback_query_handler(func=lambda call: call.data.startswith('help_'))
def callback_help(call):
    if call.data == "help_back":
        try:
            bot.edit_message_text(
                "👋 မင်္ဂလာပါ! Group Control Bot မှ ကြိုဆိုပါတယ်။ အောက်ပါ Button များကို နှိပ်၍ အမိန့်များကို ကြည့်နိုင်ပါသည်။",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=get_rose_help_markup()
            )
        except Exception:
            pass
        return

    help_texts = {
        "help_admin": "👑 **Admin & Sudo Commands**\n\n• `/addsudo` [reply/id] - Sudo user ထည့်ရန်\n• `/rmsudo` [reply/id] - Sudo user ဖြုတ်ရန်\n• `/sudolist` - Sudo User စာရင်းကြည့်ရန်\n• `/status` - Bot ရဲ့ CPU/RAM status ကြည့်ရန်",
        "help_mention": "📢 **Tag & Mention Commands**\n\n• `/all` [စာ] သို့မဟုတ် `@all` - Member အားလုံးကို Mention ခေါ်ရန်\n• `/admins` သို့မဟုတ် `@admins` - Admins အားလုံးကို ခေါ်ရန်\n• `/stopmention` - Mention ခေါ်နေခြင်းကို ရပ်ရန်",
        "help_badwords": "🚫 **Badwords Commands**\n\n• `/addbad` [word] - မကောင်းသောစာလုံး ထည့်ရန်\n• `/rmbad` [word] - ပြန်ဖြုတ်ရန်\n• `/badwords` - Badword စာရင်းကြည့်ရန်",
        "help_filters": "🎯 **Filter Commands**\n\n• `/filter` [keyword] [reply] - Auto-Reply ထည့်ရန်\n• `/stop` [keyword] - Filter ဖျက်ရန်\n• `/filters` - Filter စာရင်းကြည့်ရန်",
        "help_notes": "📝 **Notes Commands**\n\n• `/save` [notename] [content] - Note မှတ်ရန်\n• `/get` [notename] သို့မဟုတ် `#notename` - Note ကြည့်ရန်\n• `/clear` [notename] - Note ဖျက်ရန်",
        "help_warns": "⚠️ **Warning Commands**\n\n• `/warn` [reply] - သတိပေးရန်\n• `/rmwarn` [reply] - Warn လျှော့ရန်\n• `/warns` [reply] - Warn အရေအတွက်ကြည့်ရန်",
        "help_welcome": "👋 **Welcome Commands**\n\n• `/setwelcome` [စာ] - Welcome message ပြောင်းရန်",
        "help_pin": "📌 **Pin Commands**\n\n• `/pin` [reply] - Message ကို Pin ထိန်းရန်\n• `/unpin` - Pin ဖြုတ်ရန်",
        "help_mute": "🔇 **Mute Commands**\n\n• `/mute` [reply] - စာရေးခွင့် ပိတ်ရန်\n• `/unmute` [reply] - ပြန်ဖွင့်ပေးရန်",
        "help_ban": "🚫 **Ban & Kick Commands**\n\n• `/ban` [reply] - Group မှ ထုတ်ပစ်ရန် (Ban)\n• `/unban` [reply] - Unban လုပ်ရန်\n• `/kick` [reply] - Group မှ ခေတ္တ ထုတ်ရန်",
        "help_broadcast": "📢 **Broadcast Commands**\n\n• `/broadcast` [စာ] - Bot သုံးနေသည့် Group/User အားလုံးထံ စာပို့ရန်"
    }
    
    text = help_texts.get(call.data, "ℹ️ အချက်အလက် မရှိသေးပါ။")
    back_markup = InlineKeyboardMarkup()
    back_markup.add(InlineKeyboardButton("⬅️ နောက်သို့", callback_data="help_back"))
    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=back_markup)
    except Exception:
        pass

# ==========================================
# ⚙️ ALL COMMAND HANDLERS
# ==========================================

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "👋 မင်္ဂလာပါ! Group Control Bot မှ ကြိုဆိုပါတယ်။ အောက်ပါ Button များကို နှိပ်၍ အမိန့်များကို ကြည့်နိုင်ပါသည်။", reply_markup=get_rose_help_markup())

@bot.message_handler(commands=['status', 'system'])
def cmd_status(message):
    try:
        cpu_usage = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        ram = psutil.virtual_memory()
        ram_total = round(ram.total / (1024 ** 3), 2)
        ram_used = round(ram.used / (1024 ** 3), 2)
        ram_percent = ram.percent
        disk = psutil.disk_usage('/')
        disk_total = round(disk.total / (1024 ** 3), 2)
        disk_used = round(disk.used / (1024 ** 3), 2)
        disk_percent = disk.percent
        system_os = platform.system()

        status_msg = (
            "📊 **Bot System Status & Performance**\n\n"
            f"🖥 **OS:** `{system_os}`\n"
            f"⚡ **CPU Usage:** `{cpu_usage}%` ({cpu_count} Cores)\n"
            f"🧠 **RAM Usage:** `{ram_used} GB / {ram_total} GB` (`{ram_percent}%`)\n"
            f"💾 **Disk Storage:** `{disk_used} GB / {disk_total} GB` (`{disk_percent}%`)\n\n"
            "✅ **Bot Status:** Online"
        )
        bot.reply_to(message, status_msg)
    except Exception as e:
        bot.reply_to(message, f"❌ Status Error: {e}")

# SUDO SYSTEM
@bot.message_handler(commands=['addsudo'])
def cmd_addsudo(message):
    if not is_owner(message.from_user.id):
        return bot.reply_to(message, "❌ ဤ Command ကို Owner သာ သုံးနိုင်ပါသည်။")
    target_id = None
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
    else:
        parts = message.text.split()
        if len(parts) > 1 and parts[1].isdigit():
            target_id = int(parts[1])
    
    if not target_id:
        return bot.reply_to(message, "⚠️ သုံးနည်း: `/addsudo [User ID]` သို့မဟုတ် User ၏ စာကို Reply ပြန်ပါ။")
    
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
        return bot.reply_to(message, "❌ ဤ Command ကို Owner သာ သုံးနိုင်ပါသည်။")
    target_id = None
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
    else:
        parts = message.text.split()
        if len(parts) > 1 and parts[1].isdigit():
            target_id = int(parts[1])
            
    if not target_id:
        return bot.reply_to(message, "⚠️ သုံးနည်း: `/rmsudo [User ID]` သို့မဟုတ် User ၏ စာကို Reply ပြန်ပါ။")
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM sudo_users WHERE user_id = %s', (target_id,))
        conn.commit()
        cursor.close()
        conn.close()
        bot.reply_to(message, f"🗑 User `{target_id}` အား Sudo List မှ ဖြုတ်လိုက်ပါပြီ။")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

@bot.message_handler(commands=['sudolist'])
def cmd_sudolist(message):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM sudo_users')
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        text = "👑 **Sudo Users List:**\n\n"
        text += f"• **Owner:** `{OWNER_IDS[0]}`\n"
        
        if rows:
            for r in rows:
                text += f"• Sudo: `{r[0]}`\n"
        else:
            text += "\nℹ️ အခြား Sudo User များ မရှိသေးပါ။"
            
        bot.reply_to(message, text)
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

# BAN / UNBAN / KICK
@bot.message_handler(commands=['ban'])
def cmd_ban(message):
    if not is_authorized(message.from_user.id):
        return bot.reply_to(message, "❌ ခွင့်ပြုချက်မရှိပါ။")
    if not message.reply_to_message:
        return bot.reply_to(message, "⚠️ Ban ချင်သောသူ၏ Message ကို Reply ပြန်၍ ခေါ်ပေးပါ။")
    try:
        bot.ban_chat_member(message.chat.id, message.reply_to_message.from_user.id)
        bot.reply_to(message, f"🚫 [{message.reply_to_message.from_user.first_name}](tg://user?id={message.reply_to_message.from_user.id}) အား Group မှ Ban လိုက်ပါပြီ။")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

@bot.message_handler(commands=['unban'])
def cmd_unban(message):
    if not is_authorized(message.from_user.id):
        return bot.reply_to(message, "❌ ခွင့်ပြုချက်မရှိပါ။")
    if not message.reply_to_message:
        return bot.reply_to(message, "⚠️ Unban ချင်သောသူ၏ Message ကို Reply ပြန်ပေးပါ။")
    try:
        bot.unban_chat_member(message.chat.id, message.reply_to_message.from_user.id)
        bot.reply_to(message, f"✅ User ID: `{message.reply_to_message.from_user.id}` အား Unban လိုက်ပါပြီ။")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

@bot.message_handler(commands=['kick'])
def cmd_kick(message):
    if not is_authorized(message.from_user.id):
        return bot.reply_to(message, "❌ ခွင့်ပြုချက်မရှိပါ။")
    if not message.reply_to_message:
        return bot.reply_to(message, "⚠️ Kick ချင်သောသူ၏ Message ကို Reply ပြန်ပေးပါ။")
    try:
        bot.ban_chat_member(message.chat.id, message.reply_to_message.from_user.id)
        bot.unban_chat_member(message.chat.id, message.reply_to_message.from_user.id)
        bot.reply_to(message, f"👞 [{message.reply_to_message.from_user.first_name}](tg://user?id={message.reply_to_message.from_user.id}) အား Group မှ ထုတ်လိုက်ပါပြီ။")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

# MUTE / UNMUTE
@bot.message_handler(commands=['mute'])
def cmd_mute(message):
    if not is_authorized(message.from_user.id):
        return bot.reply_to(message, "❌ ခွင့်ပြုချက်မရှိပါ။")
    if not message.reply_to_message:
        return bot.reply_to(message, "⚠️ Mute ချင်သောသူ၏ Message ကို Reply ပြန်ပေးပါ။")
    try:
        bot.restrict_chat_member(message.chat.id, message.reply_to_message.from_user.id, can_send_messages=False)
        bot.reply_to(message, f"🔇 [{message.reply_to_message.from_user.first_name}](tg://user?id={message.reply_to_message.from_user.id}) အား စာရေးခွင့် ပိတ်လိုက်ပါပြီ။")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

@bot.message_handler(commands=['unmute'])
def cmd_unmute(message):
    if not is_authorized(message.from_user.id):
        return bot.reply_to(message, "❌ ခွင့်ပြုချက်မရှိပါ။")
    if not message.reply_to_message:
        return bot.reply_to(message, "⚠️ Unmute ချင်သောသူ၏ Message ကို Reply ပြန်ပေးပါ။")
    try:
        bot.restrict_chat_member(message.chat.id, message.reply_to_message.from_user.id, can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True)
        bot.reply_to(message, f"🔊 [{message.reply_to_message.from_user.first_name}](tg://user?id={message.reply_to_message.from_user.id}) အား စာရေးခွင့် ပြန်ဖွင့်ပေးလိုက်ပါပြီ။")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

# PIN / UNPIN
@bot.message_handler(commands=['pin'])
def cmd_pin(message):
    if not is_authorized(message.from_user.id):
        return bot.reply_to(message, "❌ ခွင့်ပြုချက်မရှိပါ။")
    if not message.reply_to_message:
        return bot.reply_to(message, "⚠️ Pin ထိန်းချင်သော Message ကို Reply ပြန်ပေးပါ။")
    try:
        bot.pin_chat_message(message.chat.id, message.reply_to_message.message_id)
        bot.reply_to(message, "📌 Message ကို Pin ထိန်းလိုက်ပါပြီ။")
    except Exception as e:
        bot.reply_to(message, f"❌ Pin မလုပ်နိုင်ပါ: {e}")

@bot.message_handler(commands=['unpin'])
def cmd_unpin(message):
    if not is_authorized(message.from_user.id):
        return bot.reply_to(message, "❌ ခွင့်ပြုချက်မရှိပါ။")
    try:
        bot.unpin_chat_message(message.chat.id)
        bot.reply_to(message, "📌 Pin ဖြုတ်လိုက်ပါပြီ။")
    except Exception:
        bot.reply_to(message, "⚠️ Unpin လုပ်စရာ Pinned Message မရှိပါ သို့မဟုတ် Error တက်နေပါသည်။")

# BADWORDS SYSTEM
@bot.message_handler(commands=['addbad'])
def cmd_addbad(message):
    if not is_authorized(message.from_user.id):
        return bot.reply_to(message, "❌ ခွင့်ပြုချက်မရှိပါ။")
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return bot.reply_to(message, "⚠️ သုံးနည်း: `/addbad [မကောင်းသောစာလုံး]`")
    word = parts[1].lower().strip()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO badwords (chat_id, word) VALUES (%s, %s) ON CONFLICT DO NOTHING', (message.chat.id, word))
        conn.commit()
        cursor.close()
        conn.close()
        bot.reply_to(message, f"🚫 Badword **{word}** အား ထည့်သွင်းလိုက်ပါပြီ။")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

@bot.message_handler(commands=['rmbad'])
def cmd_rmbad(message):
    if not is_authorized(message.from_user.id):
        return bot.reply_to(message, "❌ ခွင့်ပြုချက်မရှိပါ။")
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return bot.reply_to(message, "⚠️ သုံးနည်း: `/rmbad [စာလုံး]`")
    word = parts[1].lower().strip()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM badwords WHERE chat_id = %s AND word = %s', (message.chat.id, word))
        conn.commit()
        cursor.close()
        conn.close()
        bot.reply_to(message, f"🗑 Badword **{word}** အား ဖြုတ်လိုက်ပါပြီ။")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

@bot.message_handler(commands=['badwords'])
def cmd_badwords(message):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT word FROM badwords WHERE chat_id = %s', (message.chat.id,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        if rows:
            words_list = "\n".join([f"• `{r[0]}`" for r in rows])
            bot.reply_to(message, f"🚫 **Group ထဲမှ Badwords စာရင်း:**\n\n{words_list}")
        else:
            bot.reply_to(message, "ℹ️ Badwords စာရင်း မရှိသေးပါ။")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

# FILTERS SYSTEM
@bot.message_handler(commands=['filter'])
def cmd_filter(message):
    if not is_authorized(message.from_user.id):
        return bot.reply_to(message, "❌ ခွင့်ပြုချက်မရှိပါ။")
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        return bot.reply_to(message, "⚠️ သုံးနည်း: `/filter [keyword] [reply text]`")
    kw, reply_text = parts[1].lower().strip(), parts[2]
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO filters (chat_id, keyword, reply_text) VALUES (%s, %s, %s) ON CONFLICT (chat_id, keyword) DO UPDATE SET reply_text = EXCLUDED.reply_text', (message.chat.id, kw, reply_text))
        conn.commit()
        cursor.close()
        conn.close()
        bot.reply_to(message, f"🎯 Filter **{kw}** အား ထည့်သွင်းလိုက်ပါပြီ။")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

@bot.message_handler(commands=['stop'])
def cmd_stop_filter(message):
    if not is_authorized(message.from_user.id):
        return bot.reply_to(message, "❌ ခွင့်ပြုချက်မရှိပါ။")
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return bot.reply_to(message, "⚠️ သုံးနည်း: `/stop [keyword]`")
    kw = parts[1].lower().strip()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM filters WHERE chat_id = %s AND keyword = %s', (message.chat.id, kw))
        conn.commit()
        cursor.close()
        conn.close()
        bot.reply_to(message, f"🗑 Filter **{kw}** အား ဖျက်လိုက်ပါပြီ။")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

@bot.message_handler(commands=['filters'])
def cmd_filters(message):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT keyword FROM filters WHERE chat_id = %s', (message.chat.id,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        if rows:
            kw_list = "\n".join([f"• `{r[0]}`" for r in rows])
            bot.reply_to(message, f"🎯 **Group ထဲမှ Filters စာရင်း:**\n\n{kw_list}")
        else:
            bot.reply_to(message, "ℹ️ Filters စာရင်း မရှိသေးပါ။")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

# NOTES SYSTEM
@bot.message_handler(commands=['save'])
def cmd_save_note(message):
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        return bot.reply_to(message, "⚠️ သုံးနည်း: `/save [notename] [content]`")
    note_name, content = parts[1].lower(), parts[2]
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO notes (chat_id, note_name, content) VALUES (%s, %s, %s) ON CONFLICT (chat_id, note_name) DO UPDATE SET content = EXCLUDED.content', (message.chat.id, note_name, content))
        conn.commit()
        cursor.close()
        conn.close()
        bot.reply_to(message, f"✅ Note **{note_name}** အား မှတ်ထားလိုက်ပါပြီ။")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

@bot.message_handler(commands=['get'])
def cmd_get_note(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return bot.reply_to(message, "⚠️ သုံးနည်း: `/get [notename]`")
    note_name = parts[1].lower()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT content FROM notes WHERE chat_id = %s AND note_name = %s', (message.chat.id, note_name))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row:
            bot.reply_to(message, row[0])
        else:
            bot.reply_to(message, "❌ ဤ Note နာမည် ရှာမတွေ့ပါ။")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

@bot.message_handler(commands=['clear'])
def cmd_clear_note(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return bot.reply_to(message, "⚠️ သုံးနည်း: `/clear [notename]`")
    note_name = parts[1].lower()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM notes WHERE chat_id = %s AND note_name = %s', (message.chat.id, note_name))
        conn.commit()
        cursor.close()
        conn.close()
        bot.reply_to(message, f"🗑 Note **{note_name}** ကို ဖျက်လိုက်ပါပြီ။")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

# WARNINGS SYSTEM
@bot.message_handler(commands=['warn'])
def cmd_warn(message):
    if not is_authorized(message.from_user.id):
        return bot.reply_to(message, "❌ ခွင့်ပြုချက်မရှိပါ။")
    if not message.reply_to_message:
        return bot.reply_to(message, "⚠️ Warn ပေးချင်သောသူ၏ Message ကို Reply ပြန်ပေးပါ။")
    
    target_id = message.reply_to_message.from_user.id
    target_name = message.reply_to_message.from_user.first_name
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO warns (chat_id, user_id, count) VALUES (%s, %s, 1) ON CONFLICT (chat_id, user_id) DO UPDATE SET count = warns.count + 1 RETURNING count', (message.chat.id, target_id))
        count = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()

        if count >= 3:
            bot.ban_chat_member(message.chat.id, target_id)
            bot.reply_to(message, f"🚫 [{target_name}](tg://user?id={target_id}) သည် Warn ၃ ကြိမ် ပြည့်သွားသဖြင့် Group မှ Ban ขံလိုက်ရပါပြီ။")
        else:
            bot.reply_to(message, f"⚠️ [{target_name}](tg://user?id={target_id}) အား သတိပေးလိုက်ပါပြီ။\nလက်ရှိ Warn: `{count}/3`")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

@bot.message_handler(commands=['rmwarn'])
def cmd_rmwarn(message):
    if not is_authorized(message.from_user.id):
        return bot.reply_to(message, "❌ ခွင့်ပြုချက်မရှိပါ။")
    if not message.reply_to_message:
        return bot.reply_to(message, "⚠️ Warn လျှော့ချင်သောသူ၏ Message ကို Reply ပြန်ပေးပါ။")
    target_id = message.reply_to_message.from_user.id
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE warns SET count = GREATEST(0, count - 1) WHERE chat_id = %s AND user_id = %s RETURNING count', (message.chat.id, target_id))
        row = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        c = row[0] if row else 0
        bot.reply_to(message, f"✅ Warn ၁ ကြိမ် လျှော့ပေးလိုက်ပါပြီ။ လက်ရှိ Warn: `{c}/3`")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

@bot.message_handler(commands=['warns'])
def cmd_warns(message):
    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT count FROM warns WHERE chat_id = %s AND user_id = %s', (message.chat.id, target.id))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        c = row[0] if row else 0
        bot.reply_to(message, f"⚠️ [{target.first_name}](tg://user?id={target.id}) ၏ Warn အရေအတွက်: `{c}/3`")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

# WELCOME SETTING
@bot.message_handler(commands=['setwelcome'])
def cmd_setwelcome(message):
    if not is_authorized(message.from_user.id):
        return bot.reply_to(message, "❌ ခွင့်ပြုချက်မရှိပါ။")
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return bot.reply_to(message, "⚠️ သုံးနည်း: `/setwelcome [ကြိုဆိုစာ]`")
    msg = parts[1]
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO welcomes (chat_id, custom_message) VALUES (%s, %s) ON CONFLICT (chat_id) DO UPDATE SET custom_message = EXCLUDED.custom_message', (message.chat.id, msg))
        conn.commit()
        cursor.close()
        conn.close()
        bot.reply_to(message, "👋 Welcome Message အသစ် ပြောင်းလဲလိုက်ပါပြီ။")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

# BROADCAST COMMAND
@bot.message_handler(commands=['broadcast'])
def cmd_broadcast(message):
    if not is_owner(message.from_user.id):
        return bot.reply_to(message, "❌ ဤ Command ကို Owner သာ သုံးနိုင်ပါသည်။")
    
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return bot.reply_to(message, "⚠️ သုံးနည်း: `/broadcast [ပို့ချင်သည့်စာ]`")
    
    bc_text = parts[1]
    bot.reply_to(message, "📢 Broadcast စတင် ပို့ဆောင်နေပါပြီ...")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT chat_id FROM groups')
        groups = cursor.fetchall()
        cursor.execute('SELECT user_id FROM users')
        users = cursor.fetchall()
        cursor.close()
        conn.close()

        success, failed = 0, 0
        all_targets = set([g[0] for g in groups] + [u[0] for u in users])
        
        for target in all_targets:
            try:
                bot.send_message(target, f"📢 **[ Broadcast Announcement ]**\n\n{bc_text}")
                success += 1
                time.sleep(0.1)
            except Exception:
                failed += 1
                
        bot.send_message(message.chat.id, f"✅ Broadcast ပို့ဆောင်ပြီးပါပြီ။\n\n• အောင်မြင်: `{success}`\n• မအောင်မြင်: `{failed}`")
    except Exception as e:
        bot.reply_to(message, f"❌ Broadcast Error: {e}")

# MENTION ALL / ADMINS IMPROVED SYSTEM
def thread_mention_all(chat_id, text_to_send):
    mention_cancel_flags[chat_id] = False
    try:
        users_dict = {}

        # 1. Database မှ တဆင့် ယူခြင်း
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT user_id, first_name FROM users')
            for u in cursor.fetchall():
                users_dict[u[0]] = u[1]
            cursor.close()
            conn.close()
        except Exception:
            pass

        # 2. Telegram Group Admin များ (စာမရေးဖူးသူများပါ) ရယူခြင်း
        try:
            admins = bot.get_chat_administrators(chat_id)
            for adm in admins:
                if not adm.user.is_bot:
                    users_dict[adm.user.id] = adm.user.first_name
        except Exception:
            pass

        if not users_dict:
            bot.send_message(chat_id, "ℹ️ Member စာရင်း မတွေ့ရှိသေးပါ။")
            return

        user_list = list(users_dict.items())
        bot.send_message(chat_id, f"📢 စုစုပေါင်း Member (`{len(user_list)}`) ယောက်အား Mention ခေါ်ယူခြင်း စတင်ပါပြီ...")

        chunk_size = 5
        for i in range(0, len(user_list), chunk_size):
            if mention_cancel_flags.get(chat_id, False):
                bot.send_message(chat_id, "🛑 Mention ခေါ်ယူခြင်းကို ရပ်တန့်လိုက်ပါပြီ။")
                break

            chunk = user_list[i:i + chunk_size]
            mentions = [f"[{u[1]}](tg://user?id={u[0]})" for u in chunk]
            msg = f"📢 **{text_to_send}**\n\n" + " ".join(mentions)
            
            try:
                bot.send_message(chat_id, msg)
            except Exception:
                pass
            time.sleep(2.5)
    except Exception as e:
        bot.send_message(chat_id, f"❌ Mention Error: {e}")

@bot.message_handler(commands=['all', 'tagall'])
def cmd_tag_all(message):
    if not is_authorized(message.from_user.id):
        return bot.reply_to(message, "❌ ခွင့်ပြုချက်မရှိပါ။")
    parts = message.text.split(maxsplit=1)
    text_to_send = parts[1] if len(parts) > 1 else "အဖွဲ့ဝင်များအားလုံး သတိထားရန်!"
    threading.Thread(target=thread_mention_all, args=(message.chat.id, text_to_send)).start()

@bot.message_handler(commands=['cancelmention', 'stopmention'])
def cmd_cancel_mention(message):
    if not is_authorized(message.from_user.id):
        return bot.reply_to(message, "❌ ခွင့်ပြုချက်မရှိပါ။")
    mention_cancel_flags[message.chat.id] = True
    bot.reply_to(message, "🛑 Mention ခေါ်ခြင်းကို ရပ်တန့်ရန် အချက်ပြလိုက်ပါပြီ။")

@bot.message_handler(commands=['admins', 'admin'])
def cmd_tag_admins(message):
    if message.chat.type not in ['group', 'supergroup']:
        return
    parts = message.text.split(maxsplit=1)
    custom_text = parts[1] if len(parts) > 1 else "Admins များ သတိထားရန်!"
    try:
        admins = bot.get_chat_administrators(message.chat.id)
        admin_mentions = [f"[{admin.user.first_name}](tg://user?id={admin.user.id})" for admin in admins if not admin.user.is_bot]
        msg = f"👑 **{custom_text}**\n\n" + " ".join(admin_mentions)
        bot.send_message(message.chat.id, msg)
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

# ==========================================
# ALL MESSAGES HANDLER (SAVE USER / BADWORDS / FILTERS / WELCOME)
# ==========================================
@bot.message_handler(func=lambda message: True, content_types=['text', 'photo', 'video', 'document', 'animation', 'new_chat_members'])
def handle_all_messages(message):
    # Welcome New Members & Record Users
    if message.content_type == 'new_chat_members':
        for member in message.new_chat_members:
            if not member.is_bot:
                save_user(member)
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT custom_message FROM welcomes WHERE chat_id = %s', (message.chat.id,))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            
            custom_msg = row[0] if row else "👋 မင်္ဂလာပါ {name} ၊ Group မှ နွေးထွေးစွာ ကြိုဆိုပါတယ်။"
            for member in message.new_chat_members:
                if not member.is_bot:
                    welcome_text = custom_msg.replace("{name}", f"[{member.first_name}](tg://user?id={member.id})")
                    bot.send_message(message.chat.id, welcome_text)
        except Exception:
            pass
        return

    text = message.text or message.caption or ""

    if message.chat.type == 'private':
        save_user(message.from_user)
    elif message.chat.type in ['group', 'supergroup']:
        save_group(message.chat.id, message.chat.title, message.from_user.id, message.from_user.first_name)
        save_user(message.from_user)

        # Check Badwords
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT word FROM badwords WHERE chat_id = %s', (message.chat.id,))
            badwords = cursor.fetchall()
            cursor.close()
            conn.close()
            
            for bw in badwords:
                if bw[0] in text.lower():
                    bot.delete_message(message.chat.id, message.message_id)
                    bot.send_message(message.chat.id, f"⚠️ [{message.from_user.first_name}](tg://user?id={message.from_user.id}) ၊ မကောင်းသော စာလုံးများ သုံးစွဲခွင့် မရှိပါ။")
                    return
        except Exception:
            pass

        # Check Filters
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT keyword, reply_text FROM filters WHERE chat_id = %s', (message.chat.id,))
            filters = cursor.fetchall()
            cursor.close()
            conn.close()
            
            for kw, rep in filters:
                if kw in text.lower():
                    bot.reply_to(message, rep)
                    return
        except Exception:
            pass

        # Check Note Hashtag (#notename)
        if text.startswith("#"):
            note_name = text[1:].split()[0].lower()
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT content FROM notes WHERE chat_id = %s AND note_name = %s', (message.chat.id, note_name))
                row = cursor.fetchone()
                cursor.close()
                conn.close()
                if row:
                    bot.reply_to(message, row[0])
            except Exception:
                pass

        # Shortcut Mentions
        if text.strip() == "@all" and is_authorized(message.from_user.id):
            threading.Thread(target=thread_mention_all, args=(message.chat.id, "အဖွဲ့ဝင်များအားလုံး သတိထားရန်!")).start()
        elif text.strip() == "@admins":
            cmd_tag_admins(message)

# ==========================================
# START BOT
# ==========================================
if __name__ == "__main__":
    print("Starting Telegram Bot...")
    bot.infinity_polling(skip_pending=True)
