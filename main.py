import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import psycopg2
import time
import threading
import os
import io
import google.generativeai as genai
from PIL import Image
from flask import Flask

# ==========================================
# CONFIGURATION
# ==========================================
BOT_TOKEN = "8886077155:AAET1U9CXGZtaiIBLYxAutzFKFe-BkQpVno"

# Owner နှင့် Admin ID များ
ADMIN_IDS = [7974865879, 7177628115]

# Gemini API Key
GEMINI_API_KEY = "AQ.Ab8RN6KyZPxAwdKvzTfUeDI4uAPi8uPS71SWbYWU55NeExC_Bg"

FORCE_JOIN_GROUP_ID = -1004489775235
FORCE_JOIN_LINK = "https://t.me/+00J7JktW8bJlZTY1"
DATABASE_URL = "postgresql://postgres.fdfcifwziqrqqjimtqgm:zaykaunghtet704%23%40@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres"

# Setup Gemini AI
try:
    genai.configure(api_key=GEMINI_API_KEY)
    ai_model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    print(f"Gemini Setup Error: {e}")

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
# 🖼 AI CARD CHARACTER IDENTIFIER (GEMINI)
# ==========================================
def identify_card_character(message):
    try:
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        image = Image.open(io.BytesIO(downloaded_file))
        
        prompt = (
            "Identify the anime, game, or movie character in this card image. "
            "Reply strictly with only the character name. Do not add extra words or punctation."
        )
        
        response = ai_model.generate_content([prompt, image])
        char_name = response.text.strip()
        
        if char_name:
            hint_cmd = f"/guess {char_name.lower()}"
            full_cmd = f"/guess {char_name}"
            catch_cmd = f"/catch {char_name}"
            
            return (
                f"🎯 **Character Identified:**\n\n"
                f"👤 **Name:** `{char_name}`\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🔹 **Guess Hint:** `{hint_cmd}`\n"
                f"🔸 **Guess Full:** `{full_cmd}`\n"
                f"⚔️ **Catch:** `{catch_cmd}`"
            )
    except Exception as e:
        print(f"AI Identification Error: {e}")
    return None

# ==========================================
# ADMIN COMMAND HANDLERS
# ==========================================

@bot.message_handler(commands=['status'])
def cmd_status(message):
    if is_owner(message.from_user.id):
        bot.reply_to(message, "🟢 Bot is Online and Running normally!")

@bot.message_handler(commands=['stats'])
def cmd_stats(message):
    if not is_owner(message.from_user.id):
        return
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users')
        user_count = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM groups')
        group_count = cursor.fetchone()[0]
        cursor.close()
        conn.close()

        bot.reply_to(message, f"📊 **Bot Statistics**\n\n👤 Users: `{user_count}`\n👥 Groups: `{group_count}`")
    except Exception as e:
        bot.reply_to(message, f"❌ Database Error: {e}")

@bot.message_handler(commands=['groups'])
def cmd_groups(message):
    if not is_owner(message.from_user.id):
        return
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT title, added_by_name FROM groups')
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        if not rows:
            bot.reply_to(message, "👥 မည်သည့် Group မှ မရှိသေးပါ။")
            return

        text = "👥 Group List:\n\n"
        for i, row in enumerate(rows, 1):
            text += f"{i}. {row[0]} (Added by: {row[1]})\n"
        
        # Markdown Parse Error မတက်အောင် Plain Text အဖြစ် ပို့ပေးခြင်း
        bot.reply_to(message, text)
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

@bot.message_handler(commands=['broadcast'])
def cmd_broadcast(message):
    if not is_owner(message.from_user.id):
        return
    
    command_text = message.text.replace('/broadcast', '').strip()
    if not command_text and not message.reply_to_message:
        bot.reply_to(message, "⚠️ ကျေးဇူးပြု၍ စာရိုက်ပါ သို့မဟုတ် Forward/Message ကို Reply လုပ်ပြီး `/broadcast <စာ>` ပို့ပါ။")
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users')
    users = cursor.fetchall()
    cursor.close()
    conn.close()

    success, failed = 0, 0
    bot.reply_to(message, "📢 Broadcast စတင်ပို့နေပါပြီ...")

    for user in users:
        try:
            if message.reply_to_message:
                bot.copy_message(user[0], message.chat.id, message.reply_to_message.message_id)
            else:
                bot.send_message(user[0], command_text)
            success += 1
            time.sleep(0.05)
        except Exception:
            failed += 1

    bot.send_message(message.chat.id, f"✅ Broadcast အောင်မြင်ပါသည်!\n\nအောင်မြင်: {success}\nကျရှုံး: {failed}")

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

    # ၁။ ပုံပါလာလျှင် AI ဖြင့် နာမည်ရှာပေးခြင်း
    if message.photo:
        ai_result = identify_card_character(message)
        if ai_result:
            bot.reply_to(message, ai_result, parse_mode="Markdown")

    # PRIVATE CHAT LOGIC (FORWARD TO ADMINS)
    if message.chat.type == 'private':
        save_user(message.from_user)

        if not is_owner(message.from_user.id):
            user = message.from_user
            user_info = f"📩 New Message Received!\n\n👤 From: {user.first_name or ''}\n🆔 User ID: {user.id}\n🔗 Username: @{user.username or 'မရှိပါ'}"
            
            for admin_id in ADMIN_IDS:
                try:
                    bot.send_message(admin_id, user_info)
                    bot.forward_message(admin_id, message.chat.id, message.message_id)
                except Exception:
                    pass

    # COMMANDS
    if text_to_check.startswith('/start'):
        if is_owner(message.from_user.id):
            bot.reply_to(message, "👋 မင်္ဂလာပါ Admin! Control Panel ကို သုံးနိုင်ပါပြီ။ /help နှိပ်၍ ကြည့်ပါ။")
            return
        
        if not is_user_joined(message.from_user.id):
            bot.reply_to(
                message, 
                "⚠️ **သတိပေးချက်**\n\nBot ကို အသုံးပြုနိုင်ရန်အတွက် အောက်ပါ Group သို့ အရင် Join ပေးပါရန်။", 
                reply_markup=get_force_join_markup(),
                parse_mode="Markdown"
            )
        else:
            bot.reply_to(message, "👋 မင်္ဂလာပါ! ကဒ်ပုံများကို ပို့ပေးပါက AI မှ Character နာမည်နှင့် Command များကို ထုတ်ပေးပါမည်။")

    elif text_to_check.startswith('/help'):
        if not is_owner(message.from_user.id):
            return
        help_text = (
            "🛠 Admin Control Panel\n\n"
            "🟢 /status - Bot အလုပ်လုပ်နေလား စစ်ဆေးရန်\n"
            "📊 /stats - သုံးစွဲသူနှင့် ဂျီပီ စုစုပေါင်း အရေအတွက်\n"
            "👥 /groups - ဂျီပီများ၊ ထည့်သွင်းသူ စာရင်း\n"
            "📢 /broadcast <စာ> - ကြော်ငြာ ပို့ရန်"
        )
        bot.reply_to(message, help_text)

print("Bot စတင်ပွင့်နေပါပြီ...")
bot.infinity_polling(skip_pending=True)
