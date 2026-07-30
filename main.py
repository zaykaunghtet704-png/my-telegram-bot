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
ADMIN_IDS = [7974865879, 7177628115]
GEMINI_API_KEY = "AQ.Ab8RN6KyZPxAwdKvzTfUeDI4uAPi8uPS71SWbYWU55NeExC_Bg"

FORCE_JOIN_GROUP_ID = -1004489775235
FORCE_JOIN_LINK = "https://t.me/+00J7JktW8bJlZTY1"
DATABASE_URL = "postgresql://postgres.fdfcifwziqrqqjimtqgm:zaykaunghtet704%23%40@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres"

# Gemini AI Setup
try:
    genai.configure(api_key=GEMINI_API_KEY)
    ai_model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    print(f"Gemini Init Error: {e}")

bot = telebot.TeleBot(BOT_TOKEN)

# ==========================================
# 🌐 FLASK KEEP ALIVE SERVER
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
# SUPABASE DATABASE HELPERS
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

# ==========================================
# 🖼 AI CARD CHARACTER IDENTIFIER
# ==========================================
def identify_character_from_message(message):
    try:
        # မက်ဆေ့ခ်ျမှာ ပုံပါမပါ စစ်ဆေးခြင်း
        if not message.photo:
            return None

        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        image = Image.open(io.BytesIO(downloaded_file))
        
        prompt = (
            "Identify the character in this image. "
            "Reply strictly ONLY with the character name (e.g. Ada Wong, Shanks, Rem). "
            "Do NOT add any sentences, brackets, or explanations."
        )
        
        response = ai_model.generate_content([prompt, image])
        char_name = response.text.strip()
        
        if char_name:
            clean_name = char_name.replace("`", "").replace("*", "")
            hint_cmd = f"/guess {clean_name.lower()}"
            full_cmd = f"/guess {clean_name}"
            catch_cmd = f"/catch {clean_name}"
            
            return (
                f"🎯 **Character Found!**\n\n"
                f"👤 **Name:** `{clean_name}`\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🔹 **Hint:** `{hint_cmd}`\n"
                f"🔸 **Full:** `{full_cmd}`\n"
                f"⚔️ **Catch:** `{catch_cmd}`"
            )
    except Exception as e:
        print(f"AI Recognition Error: {e}")
    return None

# ==========================================
# PHOTO HANDLER
# ==========================================
@bot.message_handler(content_types=['photo'])
def handle_photos(message):
    # Group ထဲဖြစ်ပါက Group စာရင်းသွင်းခြင်း
    if message.chat.type in ['group', 'supergroup']:
        save_group(message.chat.id, message.chat.title, message.from_user.id, message.from_user.first_name)

    # AI နဲ့ Character Name ရှာခြင်း
    ai_reply = identify_character_from_message(message)
    if ai_reply:
        bot.reply_to(message, ai_reply, parse_mode="Markdown")

# ==========================================
# ADMIN COMMANDS (STATUS, STATS, GROUPS, BROADCAST)
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

        bot.reply_to(message, f"📊 Bot Statistics\n\n👤 Users: {user_count}\n👥 Groups: {group_count}")
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
        bot.reply_to(message, text)
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

@bot.message_handler(commands=['broadcast'])
def cmd_broadcast(message):
    if not is_owner(message.from_user.id):
        return
    
    command_text = message.text.replace('/broadcast', '').strip()
    if not command_text and not message.reply_to_message:
        bot.reply_to(message, "⚠️ ကျေးဇူးပြု၍ စာရိုက်ပါ သို့မဟုတ် Message ကို Reply လုပ်ပြီး `/broadcast <ကြော်ငြာစာ>` ပို့ပါ။", parse_mode="Markdown")
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users')
    users = cursor.fetchall()
    cursor.execute('SELECT chat_id FROM groups')
    groups = cursor.fetchall()
    cursor.close()
    conn.close()

    targets = [u[0] for u in users] + [g[0] for g in groups]
    success, failed = 0, 0
    
    status_msg = bot.reply_to(message, "📢 Broadcast စတင်ပို့နေပါပြီ...")

    for chat_id in targets:
        try:
            if message.reply_to_message:
                bot.copy_message(chat_id, message.chat.id, message.reply_to_message.message_id)
            else:
                bot.send_message(chat_id, command_text)
            success += 1
            time.sleep(0.05)
        except Exception:
            failed += 1

    bot.edit_message_text(f"✅ **Broadcast အောင်မြင်ပါသည်!**\n\n🎯 Total Target: {len(targets)}\n🟢 အောင်မြင်: {success}\n🔴 ကျရှုံး: {failed}", chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode="Markdown")

# ==========================================
# GENERAL TEXT HANDLER
# ==========================================
@bot.message_handler(func=lambda message: True, content_types=['text', 'video', 'document'])
def handle_other_messages(message):
    text_to_check = message.text or ""

    if message.chat.type == 'private':
        save_user(message.from_user)
    elif message.chat.type in ['group', 'supergroup']:
        save_group(message.chat.id, message.chat.title, message.from_user.id, message.from_user.first_name)

    if text_to_check.startswith('/start'):
        if is_owner(message.from_user.id):
            bot.reply_to(message, "👋 မင်္ဂလာပါ Admin! Control Panel ကို သုံးနိုင်ပါပြီ။ /help နှိပ်၍ ကြည့်ပါ။")
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
            "📢 /broadcast <စာ> - ကြော်ငြာ ပို့ရန် (User + Group အကုန်ရောက်သည်)"
        )
        bot.reply_to(message, help_text)

print("Bot စတင်ပွင့်နေပါပြီ...")
bot.infinity_polling(skip_pending=True)
