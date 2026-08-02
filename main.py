import os
import re
import time
import threading
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

FORCE_JOIN_GROUP_ID = -1004489775235
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres.fdfcifwziqrqqjimtqgm:zaykaunghtet704%23%40@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres")

bot = telebot.TeleBot(BOT_TOKEN)

# ==========================================
# SUPABASE DATABASE SETUP & HELPERS
# ==========================================
def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def init_db():
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
        CREATE TABLE IF NOT EXISTS sudo_users (
            user_id BIGINT PRIMARY KEY
        )
    ''')
    conn.commit()
    cursor.close()
    conn.close()

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
# BASIC & SUDO COMMANDS
# ==========================================
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "👋 မင်္ဂလာပါ! Group Control Bot မှ ကြိုဆိုပါတယ်။ အောက်ပါ Button များကို နှိပ်၍ အမိန့်များကို ကြည့်နိုင်ပါသည်။", reply_markup=get_rose_help_markup())

@bot.message_handler(commands=['status'])
def cmd_status(message):
    bot.reply_to(message, "✅ **Bot status:** Online (မအိပ်ဘဲ အလုပ်လုပ်နေပါသည်)", parse_mode="Markdown")

@bot.message_handler(commands=['addsudo'])
def cmd_add_sudo(message):
    if not is_owner(message.from_user.id):
        bot.reply_to(message, "❌ ဤ Command ကို **Bot Main Owner** များသာ သုံးစွဲပိုင်ခွင့်ရှိသည်။")
        return
    
    target_id = None
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
    else:
        parts = message.text.split()
        if len(parts) > 1 and parts[1].isdigit():
            target_id = int(parts[1])

    if not target_id:
        bot.reply_to(message, "⚠️ ခွင့်ပြုချင်သော သူ၏ Message ကို Reply လုပ်ပါ သို့မဟုတ် ID ရိုက်ထည့်ပါ:\nဥပမာ: `/addsudo 123456789`", parse_mode="Markdown")
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO sudo_users (user_id) VALUES (%s) ON CONFLICT DO NOTHING', (target_id,))
    conn.commit()
    cursor.close()
    conn.close()

    bot.reply_to(message, f"✅ User ID: `{target_id}` အား **Bot Commands သုံးစွဲခွင့်** ပေးလိုက်ပါပြီ။", parse_mode="Markdown")

@bot.message_handler(commands=['delsudo'])
def cmd_del_sudo(message):
    if not is_owner(message.from_user.id):
        bot.reply_to(message, "❌ ဤ Command ကို **Bot Main Owner** များသာ သုံးစွဲပိုင်ခွင့်ရှိသည်။")
        return

    target_id = None
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
    else:
        parts = message.text.split()
        if len(parts) > 1 and parts[1].isdigit():
            target_id = int(parts[1])

    if not target_id:
        bot.reply_to(message, "⚠️ ခွင့်ပြုချက် ပြန်ရုပ်သိမ်းချင်သော သူ၏ Message ကို Reply လုပ်ပါ သို့မဟုတ် ID ရိုက်ထည့်ပါ:\nဥပမာ: `/delsudo 123456789`", parse_mode="Markdown")
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM sudo_users WHERE user_id = %s', (target_id,))
    conn.commit()
    cursor.close()
    conn.close()

    bot.reply_to(message, f"🗑 User ID: `{target_id}` ၏ **Bot Commands သုံးစွဲခွင့်** အား ပြန်လည် ရုပ်သိမ်းလိုက်ပါပြီ။", parse_mode="Markdown")

@bot.message_handler(commands=['sudolist'])
def cmd_list_sudo(message):
    if not is_authorized(message.from_user.id):
        bot.reply_to(message, "❌ ဤ Command ကို အသုံးပြုပိုင်ခွင့် မရှိပါ။")
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM sudo_users')
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    if not rows:
        bot.reply_to(message, "ℹ️ Owner များမှ သုံးစွဲခွင့် ပေးထားသော အခြား User မရှိသေးပါ။")
        return

    sudo_list = "\n".join([f"• `{row[0]}`" for row in rows])
    bot.reply_to(message, f"🔑 **ခွင့်ပြုချက် ရရှိထားသော Sudo Users များ စာရင်း:**\n\n{sudo_list}", parse_mode="Markdown")

# ==========================================
# 🎯 FILTER COMMANDS
# ==========================================
@bot.message_handler(commands=['filter'])
def cmd_filter(message):
    if not is_authorized(message.from_user.id):
        bot.reply_to(message, "❌ ဤ Command ကို **Authorized User** များသာ သုံးနိုင်ပါသည်။")
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        bot.reply_to(message, "⚠️ အသုံးပြုပုံ: `/filter <စကားလုံး> <ပြန်ဖြေချင်သည့် စာ>`", parse_mode="Markdown")
        return
    
    keyword = parts[1].lower()
    reply_text = parts[2]

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO filters (chat_id, keyword, reply_text)
        VALUES (%s, %s, %s)
        ON CONFLICT (chat_id, keyword) DO UPDATE SET reply_text = EXCLUDED.reply_text
    ''', (message.chat.id, keyword, reply_text))
    conn.commit()
    cursor.close()
    conn.close()

    bot.reply_to(message, f"✅ Filter မှတ်လိုက်ပါပြီ: **{keyword}**", parse_mode="Markdown")

@bot.message_handler(commands=['stop'])
def cmd_stop_filter(message):
    if not is_authorized(message.from_user.id):
        bot.reply_to(message, "❌ ဤ Command ကို **Authorized User** များသာ သုံးနိုင်ပါသည်။")
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ အသုံးပြုပုံ: `/stop <စကားလုံး>`", parse_mode="Markdown")
        return
    
    keyword = parts[1].lower()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM filters WHERE chat_id = %s AND keyword = %s', (message.chat.id, keyword))
    conn.commit()
    cursor.close()
    conn.close()

    bot.reply_to(message, f"🗑 Filter ဖြုတ်လိုက်ပါပြီ: **{keyword}**", parse_mode="Markdown")

@bot.message_handler(commands=['filters'])
def cmd_list_filters(message):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT keyword FROM filters WHERE chat_id = %s', (message.chat.id,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    if not rows:
        bot.reply_to(message, "ℹ️ ဤ Group ထဲတွင် Filter ထည့်ထားခြင်း မရှိသေးပါ။")
        return

    filter_list = "\n".join([f"• `{row[0]}`" for row in rows])
    bot.reply_to(message, f"🎯 **Group Filter များ စာရင်း:**\n\n{filter_list}", parse_mode="Markdown")

# ==========================================
# 📝 NOTES COMMANDS
# ==========================================
@bot.message_handler(commands=['save'])
def cmd_save_note(message):
    if not is_authorized(message.from_user.id):
        bot.reply_to(message, "❌ ဤ Command ကို **Authorized User** များသာ သုံးနိုင်ပါသည်။")
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        bot.reply_to(message, "⚠️ အသုံးပြုပုံ: `/save <note_name> <content>`", parse_mode="Markdown")
        return
    
    note_name = parts[1].lower()
    content = parts[2]

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO notes (chat_id, note_name, content)
        VALUES (%s, %s, %s)
        ON CONFLICT (chat_id, note_name) DO UPDATE SET content = EXCLUDED.content
    ''', (message.chat.id, note_name, content))
    conn.commit()
    cursor.close()
    conn.close()

    bot.reply_to(message, f"📝 Note မှတ်လိုက်ပါပြီ: #{note_name}")

@bot.message_handler(commands=['get'])
def cmd_get_note(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ အသုံးပြုပုံ: `/get <note_name>`", parse_mode="Markdown")
        return
    
    note_name = parts[1].lower()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT content FROM notes WHERE chat_id = %s AND note_name = %s', (message.chat.id, note_name))
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if row:
        bot.reply_to(message, row[0], parse_mode="Markdown")
    else:
        bot.reply_to(message, "❌ ဤ Note Name ကို ရှာမတွေ့ပါ။")

@bot.message_handler(commands=['clear'])
def cmd_clear_note(message):
    if not is_authorized(message.from_user.id):
        bot.reply_to(message, "❌ ဤ Command ကို **Authorized User** များသာ သုံးနိုင်ပါသည်။")
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ အသုံးပြုပုံ: `/clear <note_name>`", parse_mode="Markdown")
        return
    
    note_name = parts[1].lower()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM notes WHERE chat_id = %s AND note_name = %s', (message.chat.id, note_name))
    conn.commit()
    cursor.close()
    conn.close()

    bot.reply_to(message, f"🗑 Note ဖျက်လိုက်ပါပြီ: #{note_name}")

@bot.message_handler(commands=['notes'])
def cmd_list_notes(message):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT note_name FROM notes WHERE chat_id = %s', (message.chat.id,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    if not rows:
        bot.reply_to(message, "ℹ️ ဤ Group ထဲတွင် Note သိမ်းထားခြင်း မရှိသေးပါ။")
        return

    notes_list = "\n".join([f"• `#{row[0]}`" for row in rows])
    bot.reply_to(message, f"📝 **Group Notes များ စာရင်း:**\n\n{notes_list}", parse_mode="Markdown")

# ==========================================
# ⚠️ WARNING COMMANDS
# ==========================================
@bot.message_handler(commands=['warn'])
def cmd_warn(message):
    if not is_authorized(message.from_user.id):
        bot.reply_to(message, "❌ ဤ Command ကို **Authorized User** များသာ သုံးနိုင်ပါသည်။")
        return
    if not message.reply_to_message:
        bot.reply_to(message, "⚠️ သတိပေးချင်သော သူ၏ Message ကို Reply ပြုလုပ်၍ အသုံးပြုပါ။")
        return
    
    target_user = message.reply_to_message.from_user
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT count FROM warns WHERE chat_id = %s AND user_id = %s', (message.chat.id, target_user.id))
    row = cursor.fetchone()
    
    count = (row[0] + 1) if row else 1
    cursor.execute('''
        INSERT INTO warns (chat_id, user_id, count)
        VALUES (%s, %s, %s)
        ON CONFLICT (chat_id, user_id) DO UPDATE SET count = EXCLUDED.count
    ''', (message.chat.id, target_user.id, count))
    conn.commit()
    cursor.close()
    conn.close()

    if count >= 3:
        try:
            bot.ban_chat_member(message.chat.id, target_user.id)
            bot.reply_to(message, f"🚫 [{target_user.first_name}](tg://user?id={target_user.id}) သည် Warning (၃) ကြိမ် ပြည့်သွားသဖြင့် Group မှ Ban လိုက်ပါပြီ။", parse_mode="Markdown")
        except Exception as e:
            bot.reply_to(message, f"⚠️ [{target_user.first_name}](tg://user?id={target_user.id}) တွင် Warning (၃) ကြိမ် ပြည့်သွားသော်လည်း Ban မရပါ: {e}", parse_mode="Markdown")
    else:
        bot.reply_to(message, f"⚠️ [{target_user.first_name}](tg://user?id={target_user.id}) အား Warning ပေးလိုက်ပါပြီ။ ({count}/3)", parse_mode="Markdown")

@bot.message_handler(commands=['warns'])
def cmd_warns_check(message):
    target_user = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT count FROM warns WHERE chat_id = %s AND user_id = %s', (message.chat.id, target_user.id))
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    count = row[0] if row else 0
    bot.reply_to(message, f"⚠️ [{target_user.first_name}](tg://user?id={target_user.id}) ၏ Warning အရေအတွက်: **{count}/3**", parse_mode="Markdown")

@bot.message_handler(commands=['resetwarns'])
def cmd_reset_warns(message):
    if not is_authorized(message.from_user.id):
        bot.reply_to(message, "❌ ဤ Command ကို **Authorized User** များသာ သုံးနိုင်ပါသည်။")
        return
    if not message.reply_to_message:
        bot.reply_to(message, "⚠️ Warning ဖျက်ပေးချင်သော သူ၏ Message ကို Reply ပြုလုပ်ပါ။")
        return

    target_user = message.reply_to_message.from_user
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM warns WHERE chat_id = %s AND user_id = %s', (message.chat.id, target_user.id))
    conn.commit()
    cursor.close()
    conn.close()

    bot.reply_to(message, f"✅ [{target_user.first_name}](tg://user?id={target_user.id}) ၏ Warning များအားလုံးကို Reset လုပ်ပေးလိုက်ပါပြီ။", parse_mode="Markdown")

# ==========================================
# 👋 WELCOME COMMAND
# ==========================================
@bot.message_handler(commands=['setwelcome'])
def cmd_set_welcome(message):
    if not is_authorized(message.from_user.id):
        bot.reply_to(message, "❌ ဤ Command ကို **Authorized User** များသာ သုံးနိုင်ပါသည်။")
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ အသုံးပြုပုံ: `/setwelcome <ကြိုဆိုသည့် စာသား>`", parse_mode="Markdown")
        return
    
    welcome_text = parts[1]
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO welcomes (chat_id, custom_message)
        VALUES (%s, %s)
        ON CONFLICT (chat_id) DO UPDATE SET custom_message = EXCLUDED.custom_message
    ''', (message.chat.id, welcome_text))
    conn.commit()
    cursor.close()
    conn.close()

    bot.reply_to(message, "👋 Welcome Message ကို ပြင်ဆင်သိမ်းဆည်းလိုက်ပါပြီ။")

# ==========================================
# MODERATION COMMANDS
# ==========================================
@bot.message_handler(commands=['pin'])
def cmd_pin(message):
    if not is_authorized(message.from_user.id):
        bot.reply_to(message, "❌ ဤ Command ကို **Authorized User** များသာ သုံးနိုင်ပါသည်။")
        return
    if not message.reply_to_message:
        bot.reply_to(message, "⚠️ Pin ထိုးချင်သော စာအား Reply လုပ်၍ `/pin` ဟု ရိုက်ပါ။", parse_mode="Markdown")
        return
    try:
        bot.pin_chat_message(message.chat.id, message.reply_to_message.message_id)
        bot.reply_to(message, "📌 Message ကို Pin ထိုးလိုက်ပါပြီ။")
    except Exception as e:
        bot.reply_to(message, "❌ Pin ထိုးမရပါ။ Bot တွင် Group Admin Power (Pin Messages) ရှိမရှိ စစ်ပေးပါ။")

@bot.message_handler(commands=['unpin'])
def cmd_unpin(message):
    if not is_authorized(message.from_user.id):
        bot.reply_to(message, "❌ ဤ Command ကို **Authorized User** များသာ သုံးနိုင်ပါသည်။")
        return
    try:
        if message.reply_to_message:
            bot.unpin_chat_message(message.chat.id, message.reply_to_message.message_id)
            bot.reply_to(message, "📌 Reply လုပ်ထားသော Message အား Unpin ဖြုတ်လိုက်ပါပြီ။")
        else:
            bot.unpin_chat_message(message.chat.id)
            bot.reply_to(message, "📌 Pin ထိုးထားသော စာအား Unpin ဖြုတ်လိုက်ပါပြီ။")
    except Exception as e:
        err_msg = str(e)
        if "message to unpin not found" in err_msg:
            bot.reply_to(message, "⚠️ Group ထဲတွင် Unpin ဖြုတ်စရာ Pin ထိုးထားသော Message မရှိပါ။")
        else:
            bot.reply_to(message, f"⚠️ သတိပေးချက်: Unpin ဖြုတ်မရပါ။ ({err_msg})")

@bot.message_handler(commands=['mute'])
def cmd_mute(message):
    if not is_authorized(message.from_user.id):
        bot.reply_to(message, "❌ ဤ Command ကို **Authorized User** များသာ သုံးနိုင်ပါသည်။")
        return
    if not message.reply_to_message:
        bot.reply_to(message, "⚠️ Mute ပိတ်ချင်သော သူ၏ စာကို Reply ပြုလုပ်ပါ။")
        return
    
    args = message.text.split()
    minutes = int(args[1]) if len(args) > 1 and args[1].isdigit() else 10
    until_time = int(time.time()) + (minutes * 60)
    try:
        bot.restrict_chat_member(message.chat.id, message.reply_to_message.from_user.id, until_date=until_time, can_send_messages=False)
        bot.reply_to(message, f"🔇 [{message.reply_to_message.from_user.first_name}](tg://user?id={message.reply_to_message.from_user.id}) အား {minutes} မိနစ် Mute လိုက်ပါပြီ။", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

@bot.message_handler(commands=['unmute'])
def cmd_unmute(message):
    if not is_authorized(message.from_user.id):
        bot.reply_to(message, "❌ ဤ Command ကို **Authorized User** များသာ သုံးနိုင်ပါသည်။")
        return
    if not message.reply_to_message:
        bot.reply_to(message, "⚠️ Unmute လုပ်ချင်သော သူ၏ စာကို Reply ပြုလုပ်ပါ။")
        return
    try:
        bot.restrict_chat_member(message.chat.id, message.reply_to_message.from_user.id, can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True)
        bot.reply_to(message, "🔊 Mute ဖြုတ်ပေးလိုက်ပါပြီ။")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

@bot.message_handler(commands=['ban', 'kick'])
def cmd_ban(message):
    if not is_authorized(message.from_user.id):
        bot.reply_to(message, "❌ ဤ Command ကို **Authorized User** များသာ သုံးနိုင်ပါသည်။")
        return
    if not message.reply_to_message:
        bot.reply_to(message, "⚠️ Group မှ ထုတ်ချင်သော သူ၏ စာကို Reply ပြုလုပ်ပါ။")
        return
    try:
        bot.ban_chat_member(message.chat.id, message.reply_to_message.from_user.id)
        bot.reply_to(message, f"🚫 [{message.reply_to_message.from_user.first_name}](tg://user?id={message.reply_to_message.from_user.id}) အား Group မှ Ban လိုက်ပါပြီ။", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

@bot.message_handler(commands=['broadcast'])
def cmd_broadcast(message):
    if not is_authorized(message.from_user.id):
        bot.reply_to(message, "❌ ဤ Command ကို **Authorized User** များသာ သုံးနိုင်ပါသည်။")
        return
    
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ အသုံးပြုပုံ: `/broadcast <ပို့ချင်သော စာသား>`", parse_mode="Markdown")
        return
    
    broadcast_text = parts[1]
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users')
    users = cursor.fetchall()
    cursor.execute('SELECT chat_id FROM groups')
    groups = cursor.fetchall()
    cursor.close()
    conn.close()

    success_users, success_groups = 0, 0
    for u in users:
        try:
            bot.send_message(u[0], broadcast_text)
            success_users += 1
            time.sleep(0.05)
        except Exception:
            pass

    for g in groups:
        try:
            bot.send_message(g[0], broadcast_text)
            success_groups += 1
            time.sleep(0.05)
        except Exception:
            pass

    bot.reply_to(message, f"📢 **Broadcast ပို့ဆောင်ပြီးပါပြီ!**\n\n👤 Users: `{success_users}`\n👥 Groups: `{success_groups}`", parse_mode="Markdown")

# ==========================================
# CALLBACK HANDLER FOR HELP MENU
# ==========================================
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    if call.data.startswith("help_"):
        back_markup = InlineKeyboardMarkup()
        back_markup.add(InlineKeyboardButton("🔙 နောက်သို့", callback_data="help_main"))

        if call.data == "help_main":
            help_text = "👋 မင်္ဂလာပါ! Group Control Bot မှ ကြိုဆိုပါတယ်။ အောက်ပါ Button များကို နှိပ်၍ အမိန့်များကို ကြည့်နိုင်ပါသည်။"
            bot.edit_message_text(help_text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_rose_help_markup())
        elif call.data == "help_filters":
            bot.edit_message_text("🎯 **Filters Commands:**\n\n- `/filter <စကားလုံး> <ပြန်ဖြေချင်သည့် စာ>`\n- `/stop <စကားလုံး>`\n- `/filters`", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=back_markup)
        elif call.data == "help_notes":
            bot.edit_message_text("📝 **Notes Commands:**\n\n- `/save <name> <content>`\n- `/get <name>` သို့မဟုတ် `#name`\n- `/clear <name>`\n- `/notes`", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=back_markup)
        elif call.data == "help_warns":
            bot.edit_message_text("⚠️ **Warnings Commands:**\n\n- `/warn` (Reply)\n- `/warns`\n- `/resetwarns` (Reply)", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=back_markup)
        elif call.data == "help_welcome":
            bot.edit_message_text("👋 **Welcome Commands:**\n\n- `/setwelcome <စာသား>`", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=back_markup)
        elif call.data == "help_admin":
            bot.edit_message_text("👑 **Sudo Permission Commands:**\n\n- `/addsudo <id>`\n- `/delsudo <id>`\n- `/sudolist`\n- `/status`", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=back_markup)
        elif call.data == "help_antilink":
            bot.edit_message_text("🛡 **Anti-Link System:**\n\nGroup အတွင်း အဖွဲ့ဝင်များ မလိုလားအပ်ဘဲ Link/Tag များ ပို့ပါက အလိုအလျောက် ဖျက်ပေးပါသည်၊", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=back_markup)
        elif call.data == "help_pin":
            bot.edit_message_text("📌 **Pin Commands:**\n\n- `/pin` (Reply)\n- `/unpin`", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=back_markup)
        elif call.data == "help_mute":
            bot.edit_message_text("🔇 **Mute Commands:**\n\n- `/mute <မိနစ်>` (Reply)\n- `/unmute` (Reply)", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=back_markup)
        elif call.data == "help_ban":
            bot.edit_message_text("🚫 **Ban / Kick Commands:**\n\n- `/ban` သို့မဟုတ် `/kick` (Reply)", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=back_markup)
        elif call.data == "help_broadcast":
            bot.edit_message_text("📢 **Broadcast Command:**\n\n- `/broadcast <စာ>`", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=back_markup)

# ==========================================
# NEW MEMBER WELCOME HANDLER
# ==========================================
@bot.message_handler(content_types=['new_chat_members'])
def welcome_new_member(message):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT custom_message FROM welcomes WHERE chat_id = %s', (message.chat.id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    welcome_text = row[0] if row else "👋 မင်္ဂလာပါ {name}, {group} မှ နွေးထွေးစွာ ကြိုဆိုပါတယ်။"
    
    for new_member in message.new_chat_members:
        formatted_msg = welcome_text.format(
            name=new_member.first_name,
            group=message.chat.title
        )
        bot.send_message(message.chat.id, formatted_msg)

# ==========================================
# ALL MESSAGES HANDLER
# ==========================================
@bot.message_handler(func=lambda message: True, content_types=['text', 'photo', 'video', 'document', 'animation'])
def handle_all_messages(message):
    text = message.text or message.caption or ""

    # 1. PRIVATE CHAT HANDLER
    if message.chat.type == 'private':
        save_user(message.from_user)
        if not is_authorized(message.from_user.id):
            for admin_id in OWNER_IDS:
                try:
                    bot.send_message(admin_id, f"📩 **Message From:** [{message.from_user.first_name}](tg://user?id={message.from_user.id})\n`ID: {message.from_user.id}`", parse_mode="Markdown")
                    bot.forward_message(admin_id, message.chat.id, message.message_id)
                except Exception:
                    pass

    # 2. GROUP CHAT HANDLER
    elif message.chat.type in ['group', 'supergroup']:
        save_group(message.chat.id, message.chat.title, message.from_user.id, message.from_user.first_name)
        
        # Anti-Link Check
        if contains_link(text) and not is_authorized(message.from_user.id):
            try:
                bot.delete_message(message.chat.id, message.message_id)
            except Exception:
                pass

        # Note hashtag check (#note_name)
        if text.startswith('#') and len(text) > 1:
            note_name = text[1:].lower()
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT content FROM notes WHERE chat_id = %s AND note_name = %s', (message.chat.id, note_name))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            if row:
                bot.reply_to(message, row[0], parse_mode="Markdown")

        # Auto-reply filter check
        if text:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT reply_text FROM filters WHERE chat_id = %s AND keyword = %s', (message.chat.id, text.lower()))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            if row:
                bot.reply_to(message, row[0])

# ==========================================
# START BOT
# ==========================================
if __name__ == "__main__":
    print("Bot is starting...")
    bot.infinity_polling(skip_pending=True)
