import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import psycopg2
import time
import threading
import re
import os
from flask import Flask

# ==========================================
# CONFIGURATION
# ==========================================
BOT_TOKEN = "8886077155:AAET1U9CXGZtaiIBLYxAutzFKFe-BkQpVno"

# Owner နှင့် Admin ID များ
ADMIN_IDS = [7974865879, 7177628115]

FORCE_JOIN_GROUP_ID = -1004489775235
FORCE_JOIN_LINK = "https://t.me/+00J7JktW8bJlZTY1"
DATABASE_URL = "postgresql://postgres.fdfcifwziqrqqjimtqgm:zaykaunghtet704%23%40@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres"

bot = telebot.TeleBot(BOT_TOKEN)

# ==========================================
# 🌐 RENDER PORT TIMEOUT FIX (FLASK WEB SERVER)
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "Bot is running 24/7 online!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()

keep_alive()

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
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"DB Init Error: {e}")

init_db()

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

def is_owner(user_id):
    return user_id in ADMIN_IDS

def is_user_joined(user_id):
    try:
        member = bot.get_chat_member(FORCE_JOIN_GROUP_ID, user_id)
        if member.status in ['creator', 'administrator', 'member']:
            return True
        return False
    except Exception:
        return True

def get_force_join_markup():
    markup = InlineKeyboardMarkup()
    btn_join = InlineKeyboardButton("📢 Join Group", url=FORCE_JOIN_LINK)
    btn_check = InlineKeyboardButton("✅ Check Joined", callback_data="check_joined")
    markup.add(btn_join)
    markup.add(btn_check)
    return markup

# ==========================================
# 🔍 TEXT BASED CARD FINDER (NO GOOGLE API)
# ==========================================
def extract_card_info(text):
    if not text:
        return None
    
    # Message ထဲတွင် NAME: သို့မဟုတ် Name: ပါဝင်လျှင် ဖတ်ထုတ်ခြင်း
    name_match = re.search(r'(?:NAME|Name|Character)\s*:\s*([^\n]+)', text, re.IGNORECASE)
    if name_match:
        char_name = name_match.group(1).strip()
        
        hint_cmd = f"/guess {char_name.lower()}"
        full_cmd = f"/guess {char_name}"
        
        reply_msg = (
            f"🎯 **Character Catcher Bot**\n\n"
            f"**NAME : {char_name}**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🔹 **Hint :** `{hint_cmd}`\n"
            f"🔸 **Full :** `{full_cmd}`"
        )
        return reply_msg
    return None

# ==========================================
# AUTOMATED HANDLERS
# ==========================================

@bot.callback_query_handler(func=lambda call: call.data == "check_joined")
def callback_check_joined(call):
    user_id = call.from_user.id
    if is_user_joined(user_id):
        bot.answer_callback_query(call.id, "✅ ကျေးဇူးတင်ပါတယ်! Group ထဲသို့ ဝင်ရောက်ပြီးပါပြီ။", show_alert=True)
        bot.edit_message_text(
            "👋 မင်္ဂလာပါ! Group ထဲသို့ အောင်မြင်စွာ ဝင်ရောက်ပြီးပါပြီ။",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
    else:
        bot.answer_callback_query(call.id, "❌ Group ထဲသို့ မဝင်ရသေးပါ။ အရင် ဝင်ရောက်ပေးပါ။", show_alert=True)

@bot.message_handler(func=lambda message: True, content_types=['text', 'photo', 'video', 'document'])
def handle_all_messages(message):
    text_to_check = message.caption or message.text or ""

    # 1. Сharacter နာမည် စာသားပါမပါ တိုက်ရိုက် စစ်ပေးခြင်း
    card_info = extract_card_info(text_to_check)
    if card_info:
        bot.reply_to(message, card_info, parse_mode="Markdown")

    # PRIVATE CHAT LOGIC (FORWARD TO ADMINS)
    if message.chat.type == 'private':
        save_user(message.from_user)

        if not is_owner(message.from_user.id):
            user = message.from_user
            user_info = f"📩 **New Message Received!**\n\n👤 **From:** {user.first_name or ''}\n🆔 **User ID:** `{user.id}`\n🔗 **Username:** @{user.username or 'မရှိပါ'}"
            
            for admin_id in ADMIN_IDS:
                try:
                    bot.send_message(admin_id, user_info, parse_mode="Markdown")
                    bot.forward_message(admin_id, message.chat.id, message.message_id)
                except Exception:
                    pass

    # COMMANDS
    if text_to_check.startswith('/start'):
        if is_owner(message.from_user.id):
            bot.reply_to(message, "👋 မင်္ဂလာပါ Admin! Control Panel ကို သုံးနိုင်ပါပြီ။")
            return
        
        if not is_user_joined(message.from_user.id):
            bot.reply_to(
                message, 
                "⚠️ **သတိပေးချက်**\n\nBot ကို အသုံးပြုနိုင်ရန်အတွက် အောက်ပါ Group သို့ အရင် Join ပေးပါရန်။", 
                reply_markup=get_force_join_markup(),
                parse_mode="Markdown"
            )
        else:
            bot.reply_to(message, "👋 မင်္ဂလာပါ! Waifu/Card Message များကို Forward လုပ်ပေးပါက Name နှင့် /guess Command ကို ထုတ်ပေးပါမည်။")

print("Bot စတင်ပွင့်နေပါပြီ...")
bot.infinity_polling(skip_pending=True)
