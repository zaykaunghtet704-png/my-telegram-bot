import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import psycopg2
import time
import threading
import re

# ==========================================
# CONFIGURATION
# ==========================================
# ⚠️ Token နှင့် Database URL ကို သီးသန့် လုံခြုံစွာ ထိန်းသိမ်းပါ
BOT_TOKEN = "YOUR_NEW_BOT_TOKEN_HERE"

# Main Owner များ (Bot ရဲ့ အဓိက ပိုင်ရှင် ၃ ယောက်)
OWNER_IDS = [7974865879, 7177628115, 8438417346]

FORCE_JOIN_GROUP_ID = -1004489775235
FORCE_JOIN_LINK = "https://t.me/+00J7JktW8bJlZTY1"
DATABASE_URL = "postgresql://postgres.fdfcifwziqrqqjimtqgm:zaykaunghtet704%23%40@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres"

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

# 🔑 Authorized Check
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

def is_user_joined(user_id):
    try:
        member = bot.get_chat_member(FORCE_JOIN_GROUP_ID, user_id)
        return member.status in ['creator', 'administrator', 'member']
    except Exception:
        return True

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

# ==========================================
# 🔄 ANTI-SLEEP SYSTEM
# ==========================================
def keep_alive():
    while True:
        time.sleep(300)
        try:
            bot.get_me()
        except Exception:
            pass

threading.Thread(target=keep_alive, daemon=True).start()

# ==========================================
# 🔗 ANTI-LINK PATTERN DETECTOR
# ==========================================
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
# AUTOMATED WELCOME HANDLERS
# ==========================================
@bot.message_handler(content_types=['new_chat_members'])
def welcome_new_member(message):
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except Exception:
        pass

    for user in message.new_chat_members:
        if user.id == bot.get_me().id:
            save_group(message.chat.id, message.chat.title, message.from_user.id, message.from_user.first_name)
            bot.send_message(message.chat.id, f"👋 မင်္ဂလာပါ! **{message.chat.title}** Group မှ ကြိုဆိုပါတယ်။", parse_mode="Markdown")
        else:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT custom_message FROM welcomes WHERE chat_id = %s', (message.chat.id,))
            row = cursor.fetchone()
            cursor.close()
            conn.close()

            if row and row[0]:
                welcome_text = row[0].format(
                    first=user.first_name or "",
                    username=f"@{user.username}" if user.username else user.first_name,
                    chat=message.chat.title
                )
            else:
                welcome_text = f"👋 မင်္ဂလာပါ [{user.first_name}](tg://user?id={user.id})\n\n**{message.chat.title}** Group မှ နွေးထွေးစွာ ကြိုဆိုပါတယ်။"
            
            bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown")

@bot.message_handler(content_types=['left_chat_member'])
def auto_clean_left_member(message):
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except Exception:
        pass

# ==========================================
# 🔑 SUDO / COMMANDS
# ==========================================
@bot.message_handler(commands=['start', 'help'])
def cmd_start_help(message):
    if message.chat.type == 'private':
        save_user(message.from_user)
        bot.send_message(
            message.chat.id,
            "👋 မင်္ဂလာပါ! Bot Help Menu မှ ကြိုဆိုပါတယ်။ အောက်ပါ Button များကို နှိပ်၍ လေ့လာနိုင်ပါသည်။",
            reply_markup=get_rose_help_markup()
        )

@bot.message_handler(func=lambda m: m.text and (m.text.startswith('/addsudo') or m.text.startswith('!addsudo')))
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

@bot.message_handler(func=lambda m: m.text and (m.text.startswith('/delsudo') or m.text.startswith('!delsudo')))
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

# ==========================================
# CALLBACK QUERIES
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
            bot.edit_message_text("🎯 **Filters Commands:**\n\n- `/filter <စကားလုံး> <ပြန်ဖြေချင်သည့် စာ>` - Auto-Reply Filter သတ်မှတ်ရန်\n- `/stop <စကားလုံး>` - Filter ဖျက်ရန်\n- `/filters` - Filter စာရင်းကြည့်ရန်", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=back_markup)
        elif call.data == "help_notes":
            bot.edit_message_text("📝 **Notes Commands:**\n\n- `/save <name> <content>` - Note မှတ်ရန်\n- `/get <name>` သို့မဟုတ် `#name` - Note ပြန်ကြည့်ရန်\n- `/clear <name>` - Note ဖျက်ရန်\n- `/notes` - Note များ စာရင်းကြည့်ရန်", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=back_markup)

# ==========================================
# MAIN MESSAGE & BOT COMMANDS HANDLER
# ==========================================
@bot.message_handler(func=lambda message: True, content_types=['text', 'photo', 'video', 'document', 'animation'])
def handle_all_messages(message):
    text_to_check = message.text or message.caption or ""

    # PRIVATE CHAT HANDLER
    if message.chat.type == 'private':
        save_user(message.from_user)
        if not is_authorized(message.from_user.id):
            user = message.from_user
            user_info = (
                f"📩 **New Message Received!**\n\n"
                f"👤 **From:** {user.first_name or ''} {user.last_name or ''}\n"
                f"🆔 **User ID:** `{user.id}`\n"
                f"🔗 **Username:** @{user.username or 'မရှိပါ'}\n\n"
                f"💬 **Message:**"
            )
            for admin_id in OWNER_IDS:
                try:
                    bot.send_message(admin_id, user_info, parse_mode="Markdown")
                    bot.forward_message(admin_id, message.chat.id, message.message_id)
                except Exception as e:
                    print(f"Error forwarding message: {e}")
        return

    # GROUP CHAT HANDLER
    if message.chat.type in ['group', 'supergroup']:
        # 1. Anti-Link System Check
        if contains_link(text_to_check) and not is_authorized(message.from_user.id):
            try:
                bot.delete_message(message.chat.id, message.message_id)
                return
            except Exception:
                pass

        # 2. Check Custom Filters Auto-Reply
        if message.text:
            word = message.text.lower().strip()
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT reply_text FROM filters WHERE chat_id = %s AND keyword = %s', (message.chat.id, word))
            row = cursor.fetchone()
            cursor.close()
            conn.close()

            if row:
                bot.reply_to(message, row[0], parse_mode="Markdown")
                return

            # 3. Check Note Handler (#notename)
            if word.startswith('#') and len(word) > 1:
                note_name = word[1:]
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT content FROM notes WHERE chat_id = %s AND note_name = %s', (message.chat.id, note_name))
                row = cursor.fetchone()
                cursor.close()
                conn.close()

                if row:
                    bot.reply_to(message, row[0], parse_mode="Markdown")

# ==========================================
# BOT START POLLING
# ==========================================
if __name__ == '__main__':
    print("🤖 Bot started successfully...")
    bot.infinity_polling(skip_pending=True)
