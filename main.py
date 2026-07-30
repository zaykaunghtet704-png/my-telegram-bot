import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import psycopg2
import time
import threading
import google.generativeai as genai
from PIL import Image
import io

# ==========================================
# CONFIGURATION
# ==========================================
BOT_TOKEN = "8886077155:AAET1U9CXGZtaiIBLYxAutzFKFe-BkQpVno"

# Owner နှင့် Admin ID များ
ADMIN_IDS = [7974865879, 7177628115]

# Gemini API Key (ပေါင်းထည့်ပေးထားပြီးပါပြီ)
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
    conn.commit()
    cursor.close()
    conn.close()

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
# 🖼 AI CARD CHARACTER IDENTIFIER
# ==========================================
def identify_card_character(message):
    try:
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        image = Image.open(io.BytesIO(downloaded_file))
        
        prompt = (
            "Identify the anime/game character in this image or card screenshot. "
            "Reply strictly in this format without extra explanation:\n\n"
            "NAME: <Character Name>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "🔹 Hint: /guess <lowercase character name>\n"
            "🔸 Full: /guess <Exact Character Name>"
        )
        
        response = ai_model.generate_content([prompt, image])
        return response.text.strip()
    except Exception as e:
        print(f"AI Identification Error: {e}")
        return None

# ==========================================
# AUTOMATED HANDLERS
# ==========================================

@bot.my_chat_member_handler()
def track_group_addition(my_chat_member):
    new_status = my_chat_member.new_chat_member.status
    chat = my_chat_member.chat
    user = my_chat_member.from_user

    if chat.type in ['group', 'supergroup']:
        if new_status in ['member', 'administrator']:
            user_fullname = f"{user.first_name or ''} {user.last_name or ''}".strip()
            if user.username:
                user_fullname += f" (@{user.username})"
            save_group(chat.id, chat.title, user.id, user_fullname)
        elif new_status in ['left', 'kicked']:
            delete_group(chat.id)

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

@bot.message_handler(func=lambda message: True, content_types=['text', 'photo', 'video', 'document', 'new_chat_members'])
def handle_all_messages(message):
    text = message.text if message.text else ""

    # 1. ပုံပါသော မက်ဆေ့ခ်ျ ရောက်လာပါက AI ဖြင့် Character Name ရှာဖွေပေးခြင်း
    if message.photo:
        # AI မှ Card နာမည် ရှာခိုင်းခြင်း
        ai_result = identify_card_character(message)
        if ai_result:
            bot.reply_to(message, f"🎯 **Card Finder Result:**\n\n{ai_result}", parse_mode="Markdown")

    # PRIVATE CHAT LOGIC (FORWARD TO ADMINS)
    if message.chat.type == 'private':
        save_user(message.from_user)

        if not is_owner(message.from_user.id):
            user = message.from_user
            user_info = f"📩 **New Message Received!**\n\n👤 **From:** {user.first_name or ''} {user.last_name or ''}\n🆔 **User ID:** `{user.id}`\n🔗 **Username:** @{user.username or 'မရှိပါ'}"
            
            for admin_id in ADMIN_IDS:
                try:
                    bot.send_message(admin_id, user_info, parse_mode="Markdown")
                    bot.forward_message(admin_id, message.chat.id, message.message_id)
                except Exception as e:
                    print(f"Error forwarding to admin {admin_id}: {e}")

    elif message.chat.type in ['group', 'supergroup']:
        user_fullname = f"{message.from_user.first_name or ''} {message.from_user.last_name or ''}".strip()
        if message.from_user.username:
            user_fullname += f" (@{message.from_user.username})"
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT added_by_id FROM groups WHERE chat_id = %s', (message.chat.id,))
            row = cursor.fetchone()
            cursor.close()
            conn.close()

            if not row:
                save_group(message.chat.id, message.chat.title, message.from_user.id, user_fullname)
        except Exception:
            pass

    # COMMANDS
    if text.startswith('/start'):
        if is_owner(message.from_user.id):
            bot.reply_to(message, "👋 မင်္ဂလာပါ Admin! ကြော်ငြာများ ပို့ရန်နှင့် စာရင်းများကြည့်ရန် /help ကို နှိပ်ပါ။")
            return
        
        if not is_user_joined(message.from_user.id):
            bot.reply_to(
                message, 
                "⚠️ **သတိပေးချက်**\n\nBot ကို အသုံးပြုနိုင်ရန်အတွက် အောက်ပါ Group သို့ အရင် Join ပေးပါရန် မေတ္တာရပ်ခံအပ်ပါသည်။", 
                reply_markup=get_force_join_markup(),
                parse_mode="Markdown"
            )
        else:
            bot.reply_to(message, "👋 မင်္ဂလာပါ! ကဒ်ပုံများကို ပို့ပေးပါက AI မှ နာမည် အလိုအလျောက် ရှာဖွေပေးပါမည်။")

    elif text.startswith('/help'):
        if not is_owner(message.from_user.id):
            return
        help_text = (
            "🛠 **Admin Control Panel**\n\n"
            "🟢 `/status` - Bot အလုပ်လုပ်နေလား စစ်ဆေးရန်\n"
            "📊 `/stats` - သုံးစွဲသူနှင့် ဂျီပီ စုစုပေါင်း အရေအတွက်\n"
            "👥 `/groups` - ဂျီပီများ၊ ထည့်သွင်းသူနှင့် လူဦးရေ စာရင်း\n"
            "📢 `/broadcast <စာ>` - ကြော်ငြာ စာ/ပုံ/ဗီဒီယို ပို့ရန်"
        )
        bot.reply_to(message, help_text, parse_mode="Markdown")

print("Bot စတင်ပွင့်နေပါပြီ...")
bot.infinity_polling(skip_pending=True)
