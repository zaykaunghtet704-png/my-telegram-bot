import os
import re
import time
import threading
import psycopg2
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask

# ==========================================
# 🌐 KEEP ALIVE WEB SERVER FOR RENDER (PORT SCAN FIX)
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

# Render Port Scan မိပြီး Bot ငြိမ်းမသွားစေရန် Web Server စတင်ခြင်း
keep_alive()

# ==========================================
# CONFIGURATION
# ==========================================
# Render Environment Variable သို့မဟုတ် Hardcoded Token ကို ယူမည်
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8886077155:AAET1U9CXGZtaiIBLYxAutzFKFe-BkQpVno")

# Main Owner များ (Bot ရဲ့ အဓိက ပိုင်ရှင် ၃ ယောက်)
OWNER_IDS = [7974865879, 7177628115, 8438417346]

FORCE_JOIN_GROUP_ID = -1004489775235
FORCE_JOIN_LINK = "https://t.me/+00J7JktW8bJlZTY1"
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

# 🔑 Authorized/Sudo Check
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

def delete_user(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM users WHERE user_id = %s', (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error deleting user: {e}")

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

def delete_group(chat_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM groups WHERE chat_id = %s', (chat_id,))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error deleting group: {e}")

def is_user_joined(user_id):
    try:
        member = bot.get_chat_member(FORCE_JOIN_GROUP_ID, user_id)
        return member.status in ['creator', 'administrator', 'member']
    except Exception:
        return True

def get_force_join_markup():
    markup = InlineKeyboardMarkup()
    btn_join = InlineKeyboardButton("📢 Group သို့ဝင်ရန်", url=FORCE_JOIN_LINK)
    btn_check = InlineKeyboardButton("✅ ဝင်ပြီးပါပြီ စစ်ရန်", callback_data="check_joined")
    markup.add(btn_join)
    markup.add(btn_check)
    return markup

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
# AUTOMATED TRACKING & WELCOME HANDLERS
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

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "👋 မင်္ဂလာပါ! Group Control Bot မှ ကြိုဆိုပါတယ်။ အောက်ပါ Button များကို နှိပ်၍ အမိန့်များကို ကြည့်နိုင်ပါသည်။", reply_markup=get_rose_help_markup())

# ==========================================
# 🔑 SUDO / USER AUTHORIZATION COMMANDS (OWNER ONLY)
# ==========================================
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

@bot.message_handler(func=lambda m: m.text and (m.text.startswith('/sudolist') or m.text.startswith('!sudolist')))
def cmd_list_sudo(message):
    if not is_authorized(message.from_user.id):
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
# CALLBACK QUERIES
# ==========================================
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id

    if call.data == "check_joined":
        if is_user_joined(user_id):
            bot.answer_callback_query(call.id, "✅ ကျေးဇူးတင်ပါတယ်! Group ထဲသို့ ဝင်ရောက်ပြီးပါပြီ။", show_alert=True)
            bot.edit_message_text("👋 မင်္ဂလာပါ! Group ထဲသို့ အောင်မြင်စွာ ဝင်ရောက်ပြီးပါပြီ။", chat_id=call.message.chat.id, message_id=call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "❌ Group ထဲသို့ မဝင်ရသေးပါ။ အရင် ဝင်ရောက်ပေးပါ။", show_alert=True)

    elif call.data.startswith("help_"):
        back_markup = InlineKeyboardMarkup()
        back_markup.add(InlineKeyboardButton("🔙 နောက်သို့", callback_data="help_main"))

        if call.data == "help_main":
            help_text = "👋 မင်္ဂလာပါ! Group Control Bot မှ ကြိုဆိုပါတယ်။ အောက်ပါ Button များကို နှိပ်၍ အမိန့်များကို ကြည့်နိုင်ပါသည်။"
            bot.edit_message_text(help_text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_rose_help_markup())
        elif call.data == "help_filters":
            bot.edit_message_text("🎯 **Filters Commands:**\n\n- `/filter <စကားလုံး> <ပြန်ဖြေချင်သည့် စာ>` - Auto-Reply Filter သတ်မှတ်ရန် (Auth User Only)\n- `/stop <စကားလုံး>` - Filter ဖျက်ရန် (Auth User Only)\n- `/filters` - Filter စာရင်းကြည့်ရန်", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=back_markup)
        elif call.data == "help_notes":
            bot.edit_message_text("📝 **Notes Commands:**\n\n- `/save <name> <content>` - Note မှတ်ရန် (Auth User Only)\n- `/get <name>` သို့မဟုတ် `#name` - Note ပြန်ကြည့်ရန်\n- `/clear <name>` - Note ဖျက်ရန် (Auth User Only)\n- `/notes` - Note များ စာရင်းကြည့်ရန်", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=back_markup)
        elif call.data == "help_warns":
            bot.edit_message_text("⚠️ **Warnings Commands:**\n\n- `/warn` - Reply လုပ်ပြီး သတိပေးရန် (Auth User Only)\n- `/warns` - Warning စာရင်းစစ်ရန်\n- `/resetwarns` - Warning များ ပြန်ရှင်းရန် (Auth User Only)", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=back_markup)
        elif call.data == "help_welcome":
            bot.edit_message_text("👋 **Welcome Commands:**\n\n- `/setwelcome <စာသား>` - ကြိုဆိုစာ ပြောင်းရန် (Auth User Only)", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=back_markup)
        elif call.data == "help_admin":
            bot.edit_message_text("👑 **Sudo Permission Commands:**\n\n- `/addsudo <id>` - Bot သုံးခွင့်ပေးရန် (Owner Only)\n- `/delsudo <id>` - သုံးခွင့် ပြန်ရုပ်သိမ်းရန် (Owner Only)\n- `/sudolist` - သုံးခွင့်ရှိသူများ စာရင်းကြည့်ရန်\n- `/status` - Bot Online စစ်ရန်", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=back_markup)
        elif call.data == "help_antilink":
            bot.edit_message_text("🛡 **Anti-Link System:**\n\nGroup အတွင်း အဖွဲ့ဝင်များ (Owner/Sudo မှလွဲ၍) မလိုလားအပ်ဘဲ Link သို့မဟုတ် Tag များ ပို့ပါက အလိုအလျောက် ဖျက်ပေးပါသည်။", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=back_markup)
        elif call.data == "help_pin":
            bot.edit_message_text("📌 **Pin Commands:**\n\n- `/pin` - Message ကို Reply ပြုလုပ်ပြီး Pin ထိုးရန် (Auth User Only)\n- `/unpin` - Pin ဖြုတ်ရန် (Auth User Only)", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=back_markup)
        elif call.data == "help_mute":
            bot.edit_message_text("🔇 **Mute Commands:**\n\n- `/mute <မိနစ်>` - Reply လုပ်ထားသူအား Mute ရန် (Auth User Only)\n- `/unmute` - Mute ဖြုတ်ပေးရန် (Auth User Only)", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=back_markup)
        elif call.data == "help_ban":
            bot.edit_message_text("🚫 **Ban / Kick Commands:**\n\n- `/ban` သို့မဟုတ် `/kick` - Reply လုပ်ထားသူအား Group မှ Ban ထုတ်ရန် (Auth User Only)", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=back_markup)
        elif call.data == "help_broadcast":
            bot.edit_message_text("📢 **Broadcast Command:**\n\n- `/broadcast <စာ>` - အသုံးပြုသူများနှင့် Group များအားလုံးသို့ ကြော်ငြာ ပို့ရန် (Auth User Only)", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=back_markup)

# ==========================================
# 🎯 FILTERS SYSTEM COMMANDS (AUTH USER ONLY)
# ==========================================
@bot.message_handler(func=lambda m: m.text and (m.text.startswith('/filter') or m.text.startswith('!filter')) and not m.text.startswith('/filters'))
def cmd_add_filter(message):
    if not is_authorized(message.from_user.id):
        bot.reply_to(message, "❌ ဤ Command ကို **ခွင့်ပြုချက်ရရှိထားသူ (Authorized User)** များသာ အသုံးပြုနိုင်ပါသည်။")
        return
    
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        bot.reply_to(message, "⚠️ အသုံးပြုပုံ: `/filter <စကားလုံး> <ပြန်ဖြေချင်သည့် စာ>`\nဥပမာ: `/filter နယူး ကြိုဆိုပါတယ်`", parse_mode="Markdown")
        return
    
    keyword = parts[1].lower()
    reply_text = parts[2]

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO filters (chat_id, keyword, reply_text) VALUES (%s, %s, %s)
        ON CONFLICT (chat_id, keyword) DO UPDATE SET reply_text = EXCLUDED.reply_text
    ''', (message.chat.id, keyword, reply_text))
    conn.commit()
    cursor.close()
    conn.close()

    bot.reply_to(message, f"✅ Filter **'{keyword}'** အား သတ်မှတ်လိုက်ပါပြီ။", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text and (m.text.startswith('/stop') or m.text.startswith('!stop')))
def cmd_stop_filter(message):
    if not is_authorized(message.from_user.id):
        bot.reply_to(message, "❌ ဤ Command ကို **ခွင့်ပြုချက်ရရှိထားသူ (Authorized User)** များသာ အသုံးပြုနိုင်ပါသည်။")
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

    bot.reply_to(message, f"🗑 Filter **'{keyword}'** အား ဖျက်လိုက်ပါပြီ။", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text and (m.text.startswith('/filters') or m.text.startswith('!filters')))
def cmd_get_filters(message):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT keyword FROM filters WHERE chat_id = %s', (message.chat.id,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    if not rows:
        bot.reply_to(message, "ℹ️ ဤ Group တွင် သတ်မှတ်ထားသော Filter မရှိသေးပါ။")
        return

    filter_list = "\n".join([f"• `{row[0]}`" for row in rows])
    bot.reply_to(message, f"🎯 **Group Auto-Reply Filters စာရင်း:**\n\n{filter_list}", parse_mode="Markdown")

# ==========================================
# 📝 NOTES & WARNINGS & WELCOME COMMANDS
# ==========================================
@bot.message_handler(func=lambda m: m.text and (m.text.startswith('/save') or m.text.startswith('!save')))
def cmd_save_note(message):
    if not is_authorized(message.from_user.id):
        bot.reply_to(message, "❌ ဤ Command ကို **ခွင့်ပြုချက်ရရှိထားသူ (Authorized User)** များသာ အသုံးပြုနိုင်ပါသည်။")
        return
    
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        bot.reply_to(message, "⚠️ အသုံးပြုပုံ: `/save <note_name> <အကြောင်းအရာ>`", parse_mode="Markdown")
        return
    note_name = parts[1].lower()
    content = parts[2]
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO notes (chat_id, note_name, content) VALUES (%s, %s, %s)
        ON CONFLICT (chat_id, note_name) DO UPDATE SET content = EXCLUDED.content
    ''', (message.chat.id, note_name, content))
    conn.commit()
    cursor.close()
    conn.close()
    
    bot.reply_to(message, f"✅ Note **#{note_name}** အား သိမ်းဆည်းလိုက်ပါပြီ။", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text and (m.text.startswith('/clear') or m.text.startswith('!clear')))
def cmd_clear_note(message):
    if not is_authorized(message.from_user.id):
        bot.reply_to(message, "❌ ဤ Command ကို **ခွင့်ပြုချက်ရရှိထားသူ (Authorized User)** များသာ အသုံးပြုနိုင်ပါသည်။")
        return
    
    parts = message.text.split()
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
    
    bot.reply_to(message, f"🗑 Note **#{note_name}** အား ဖျက်လိုက်ပါပြီ။", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text and (m.text.startswith('/notes') or m.text.startswith('!notes')))
def cmd_get_notes(message):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT note_name FROM notes WHERE chat_id = %s', (message.chat.id,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    if not rows:
        bot.reply_to(message, "ℹ️ ဤ Group တွင် မှတ်ထားသော Note မရှိသေးပါ။")
        return
    
    note_list = "\n".join([f"• `#{row[0]}`" for row in rows])
    bot.reply_to(message, f"📝 **Group မှတ်စု (Notes) များ:**\n\n{note_list}\n\nကြည့်ရှုရန် `/get <note_name>` သို့မဟုတ် `#{'note_name'}` ဟု ရိုက်ပါ။", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text and (m.text.startswith('/get') or m.text.startswith('!get')))
def cmd_get_single_note(message):
    parts = message.text.split()
    if len(parts) > 1:
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
            bot.reply_to(message, f"❌ **#{note_name}** အမည်ဖြင့် Note မရှိသေးပါ။", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text and (m.text.startswith('/warn') or m.text.startswith('!warn')) and not m.text.startswith('/warns'))
def cmd_warn(message):
    if not is_authorized(message.from_user.id):
        bot.reply_to(message, "❌ ဤ Command ကို **ခွင့်ပြုချက်ရရှိထားသူ (Authorized User)** များသာ အသုံးပြုနိုင်ပါသည်။")
        return
    
    if not message.reply_to_message:
        bot.reply_to(message, "⚠️ သတိပေးချင်သော သူ၏ Message ကို Reply ပြုလုပ်၍ အသုံးပြုပါ။")
        return
    
    target_user = message.reply_to_message.from_user
    if is_authorized(target_user.id):
        bot.reply_to(message, "❌ Authorized User များကို Warn ပေး၍ မရပါ။")
        return
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO warns (chat_id, user_id, count) VALUES (%s, %s, 1)
        ON CONFLICT (chat_id, user_id) DO UPDATE SET count = warns.count + 1
        RETURNING count
    ''', (message.chat.id, target_user.id))
    warn_count = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()
    
    if warn_count >= 3:
        until_time = int(time.time()) + 86400
        try:
            bot.restrict_chat_member(message.chat.id, target_user.id, until_date=until_time, can_send_messages=False)
            bot.reply_to(message, f"🚫 [{target_user.first_name}](tg://user?id={target_user.id}) သည် Warning (၃) ကြိမ် ပြည့်သွားသည့်အတွက် 24 နာရီ Mute ခံလိုက်ရပါပြီ။", parse_mode="Markdown")
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM warns WHERE chat_id = %s AND user_id = %s', (message.chat.id, target_user.id))
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            bot.reply_to(message, f"❌ Error: {e}")
    else:
        bot.reply_to(message, f"⚠️ [{target_user.first_name}](tg://user?id={target_user.id}) အား သတိပေးလိုက်ပါပြီ။\n**Warning Count:** ({warn_count}/3)", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text and (m.text.startswith('/warns') or m.text.startswith('!warns')))
def cmd_check_warns(message):
    user_id = message.reply_to_message.from_user.id if message.reply_to_message else message.from_user.id
    user_name = message.reply_to_message.from_user.first_name if message.reply_to_message else message.from_user.first_name
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT count FROM warns WHERE chat_id = %s AND user_id = %s', (message.chat.id, user_id))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    
    count = row[0] if row else 0
    bot.reply_to(message, f"📊 [{user_name}](tg://user?id={user_id}) ရရှိထားသော Warning Count: **({count}/3)**", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text and (m.text.startswith('/resetwarns') or m.text.startswith('!resetwarns')))
def cmd_reset_warns(message):
    if not is_authorized(message.from_user.id):
        bot.reply_to(message, "❌ ဤ Command ကို **ခွင့်ပြုချက်ရရှိထားသူ (Authorized User)** များသာ အသုံးပြုနိုင်ပါသည်။")
        return
    
    if not message.reply_to_message:
        bot.reply_to(message, "⚠️ Warning ဖျက်ပေးချင်သော သူ၏ Message ကို Reply ပြုလုပ်၍ အသုံးပြုပါ။")
        return
    
    target_user = message.reply_to_message.from_user
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM warns WHERE chat_id = %s AND user_id = %s', (message.chat.id, target_user.id))
    conn.commit()
    cursor.close()
    conn.close()
    
    bot.reply_to(message, f"✅ [{target_user.first_name}](tg://user?id={target_user.id}) ၏ Warnings များကို ပြန်လည်ရှင်းလင်းပေးလိုက်ပါပြီ။", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text and (m.text.startswith('/setwelcome') or m.text.startswith('!setwelcome')))
def cmd_set_welcome(message):
    if not is_authorized(message.from_user.id):
        bot.reply_to(message, "❌ ဤ Command ကို **ခွင့်ပြုချက်ရရှိထားသူ (Authorized User)** များသာ အသုံးပြုနိုင်ပါသည်။")
        return
    
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ အသုံးပြုပုံ: `/setwelcome မင်္ဂလာပါ {first} ရေ {chat} မှ ကြိုဆိုပါတယ်!`", parse_mode="Markdown")
        return
    
    custom_msg = parts[1]
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO welcomes (chat_id, custom_message) VALUES (%s, %s)
        ON CONFLICT (chat_id) DO UPDATE SET custom_message = EXCLUDED.custom_message
    ''', (message.chat.id, custom_msg))
    conn.commit()
    cursor.close()
    conn.close()
    
    bot.reply_to(message, "✅ Custom Welcome Message ကို အောင်မြင်စွာ ပြောင်းလဲလိုက်ပါပြီ။", parse_mode="Markdown")

# ==========================================
# MODERATION COMMANDS (AUTH USER ONLY)
# ==========================================
@bot.message_handler(func=lambda m: m.text and (m.text.startswith('/pin') or m.text.startswith('!pin')))
def cmd_pin(message):
    if not is_authorized(message.from_user.id):
        bot.reply_to(message, "❌ ဤ Command ကို **ခွင့်ပြုချက်ရရှိထားသူ (Authorized User)** များသာ အသုံးပြုနိုင်ပါသည်။")
        return
    
    if message.reply_to_message:
        try:
            bot.pin_chat_message(message.chat.id, message.reply_to_message.message_id)
            bot.reply_to(message, "📌 Message ကို Pin ထိုးလိုက်ပါပြီ။")
        except Exception:
            bot.reply_to(message, "❌ Pin ထိုးမရပါ: Bot ကို Admin အခွင့်အရေး ပေးထားပါသလား။")

@bot.message_handler(func=lambda m: m.text and (m.text.startswith('/unpin') or m.text.startswith('!unpin')))
def cmd_unpin(message):
    if not is_authorized(message.from_user.id):
        bot.reply_to(message, "❌ ဤ Command ကို **ခွင့်ပြုချက်ရရှိထားသူ (Authorized User)** များသာ အသုံးပြုနိုင်ပါသည်။")
        return
    
    try:
        bot.unpin_chat_message(message.chat.id)
        bot.reply_to(message, "📌 Pin ဖြုတ်လိုက်ပါပြီ။")
    except Exception:
        pass

@bot.message_handler(func=lambda m: m.text and (m.text.startswith('/mute') or m.text.startswith('!mute')))
def cmd_mute(message):
    if not is_authorized(message.from_user.id):
        bot.reply_to(message, "❌ ဤ Command ကို **ခွင့်ပြုချက်ရရှိထားသူ (Authorized User)** များသာ အသုံးပြုနိုင်ပါသည်။")
        return
    
    if message.reply_to_message:
        args = message.text.split()
        minutes = int(args[1]) if len(args) > 1 and args[1].isdigit() else 10
        until_time = int(time.time()) + (minutes * 60)
        try:
            bot.restrict_chat_member(message.chat.id, message.reply_to_message.from_user.id, until_date=until_time, can_send_messages=False)
            bot.reply_to(message, f"🔇 [{message.reply_to_message.from_user.first_name}](tg://user?id={message.reply_to_message.from_user.id}) အား {minutes} မိနစ် Mute လိုက်ပါပြီ။", parse_mode="Markdown")
        except Exception as e:
            bot.reply_to(message, f"❌ Error: {e}")

@bot.message_handler(func=lambda m: m.text and (m.text.startswith('/unmute') or m.text.startswith('!unmute')))
def cmd_unmute(message):
    if not is_authorized(message.from_user.id):
        bot.reply_to(message, "❌ ဤ Command ကို **ခွင့်ပြုချက်ရရှိထားသူ (Authorized User)** များသာ အသုံးပြုနိုင်ပါသည်။")
        return
    
    if message.reply_to_message:
        try:
            bot.restrict_chat_member(message.chat.id, message.reply_to_message.from_user.id, can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True)
            bot.reply_to(message, "🔊 Mute ဖြုတ်ပေးလိုက်ပါပြီ။")
        except Exception as e:
            bot.reply_to(message, f"❌ Error: {e}")

@bot.message_handler(func=lambda m: m.text and (m.text.startswith('/ban') or m.text.startswith('!ban') or m.text.startswith('/kick') or m.text.startswith('!kick')))
def cmd_ban(message):
    if not is_authorized(message.from_user.id):
        bot.reply_to(message, "❌ ဤ Command ကို **ခွင့်ပြုချက်ရရှိထားသူ (Authorized User)** များသာ အသုံးပြုနိုင်ပါသည်။")
        return
    
    if message.reply_to_message:
        try:
            bot.ban_chat_member(message.chat.id, message.reply_to_message.from_user.id)
            bot.reply_to(message, f"🚫 [{message.reply_to_message.from_user.first_name}](tg://user?id={message.reply_to_message.from_user.id}) အား Group မှ Ban လိုက်ပါပြီ။", parse_mode="Markdown")
        except Exception as e:
            bot.reply_to(message, f"❌ Error: {e}")

# ==========================================
# MAIN MESSAGE & BOT COMMANDS HANDLER
# ==========================================
@bot.message_handler(func=lambda message: True, content_types=['text', 'photo', 'video', 'document', 'animation', 'new_chat_members'])
def handle_all_messages(message):
    text_to_check = message.text or message.caption or ""

    # PRIVATE CHAT
    if message.chat.type == 'private':
        save_user(message.from_user)
        if not is_authorized(message.from_user.id):
            user = message.from_user
            user_info = f"📩 **New Message Received!**\n\n👤 **From:** {user.first_name or ''}\n🆔 **User ID:** `{user.id}`\n🔗 **Username:** @{user.username or 'မရှိပါ'}\n\n💬 **Message:**"
            for admin_id in OWNER_IDS:
                try:
                    bot.send_message(admin_id, user_info, parse_mode="Markdown")
                    bot.forward_message(admin_id, message.chat.id, message.message_id)
                except Exception:
                    pass
        return

    # GROUP CHAT
    if message.chat.type in ['group', 'supergroup']:
        # ANTI-LINK CHECK
        if contains_link(text_to_check):
            if not is_authorized(message.from_user.id):
                try:
                    bot.delete_message(message.chat.id, message.message_id)
                    warning_msg = bot.send_message(message.chat.id, f"⚠️ [{message.from_user.first_name}](tg://user?id={message.from_user.id}) - Group အတွင်း Link / Mention ပို့ခွင့်မရှိပါ။", parse_mode="Markdown")
                    time.sleep(5)
                    bot.delete_message(message.chat.id, warning_msg.message_id)
                except Exception:
                    pass
                return

        # AUTO-REPLY FILTERS
        if text_to_check:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT reply_text FROM filters WHERE chat_id = %s AND keyword = %s', (message.chat.id, text_to_check.lower()))
            row = cursor.fetchone()
            cursor.close()
            conn.close()

            if row:
                bot.reply_to(message, row[0])

# ==========================================
# BOT STARTING (INFINITY POLLING)
# ==========================================
if __name__ == "__main__":
    print("Bot starting...")
    bot.infinity_polling(skip_pending=True)
