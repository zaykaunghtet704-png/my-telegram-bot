import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import psycopg2
import time
import threading
import re

# ==========================================
# CONFIGURATION
# ==========================================
BOT_TOKEN = "8886077155:AAET1U9CXGZtaiIBLYxAutzFKFe-BkQpVno"

# Owner နှင့် Co-Owner (Admin ID များ စာရင်း)
ADMIN_IDS = [7974865879, 7177628115]

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

def is_group_admin(chat_id, user_id):
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ['creator', 'administrator'] or is_owner(user_id)
    except Exception:
        return False

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
# 👥 GROUP AUTOMATION HANDLERS (NEW FEATURES)
# ==========================================

# 1. Welcome Message & Auto-delete "Joined Group" message
@bot.message_handler(content_types=['new_chat_members'])
def welcome_new_member(message):
    try:
        # Group joined message ကို အမှိုက်ရှင်းသည့်အနေဖြင့် ဖျက်ပါမည်
        bot.delete_message(message.chat.id, message.message_id)
    except Exception:
        pass

    for user in message.new_chat_members:
        # Bot ကိုယ်တိုင် Group ထဲ ရောက်လာပါက
        if user.id == bot.get_me().id:
            save_group(message.chat.id, message.chat.title, message.from_user.id, message.from_user.first_name)
            bot.send_message(message.chat.id, f"👋 မင်္ဂလာပါ! **{message.chat.title}** ဂျီပီမှာ Bot ကို Admin အရာရှိအဖြစ် ခန့်အပ်ပေးပါရန်။", parse_mode="Markdown")
        else:
            welcome_text = f"👋 မင်္ဂလာပါ [{user.first_name}](tg://user?id={user.id})\n\n**{message.chat.title}** ဂျီပီမှ နွေးထွေးစွာ ကြိုဆိုပါတယ်။"
            bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown")

# 2. Auto-delete "Left Group" message
@bot.message_handler(content_types=['left_chat_member'])
def auto_clean_left_member(message):
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except Exception:
        pass

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

# ==========================================
# MAIN MESSAGE HANDLER
# ==========================================
@bot.message_handler(func=lambda message: True, content_types=['text', 'photo', 'video', 'document'])
def handle_all_messages(message):
    text = message.text if message.text else ""

    # PRIVATE CHAT LOGIC
    if message.chat.type == 'private':
        save_user(message.from_user)

        if not is_owner(message.from_user.id):
            user = message.from_user
            user_info = f"📩 **New Message Received!**\n\n👤 **From:** {user.first_name or ''} {user.last_name or ''}\n🆔 **User ID:** `{user.id}`\n🔗 **Username:** @{user.username or 'မရှိပါ'}\n\n💬 **Message:**"
            
            for admin_id in ADMIN_IDS:
                try:
                    bot.send_message(admin_id, user_info, parse_mode="Markdown")
                    bot.forward_message(admin_id, message.chat.id, message.message_id)
                except Exception as e:
                    print(f"Error forwarding: {e}")

    # GROUP CHAT LOGIC
    elif message.chat.type in ['group', 'supergroup']:
        # 1. Anti-Link (Group ထဲတွင် Link လာဖြန့်ပါက ဖျက်ခြင်း)
        if not is_group_admin(message.chat.id, message.from_user.id):
            if re.search(r'(https?://|t\.me/|telegram\.me/)', text, re.IGNORECASE):
                try:
                    bot.delete_message(message.chat.id, message.message_id)
                    bot.send_message(message.chat.id, f"⚠️ [{message.from_user.first_name}](tg://user?id={message.from_user.id}) ဂျီပီထဲတွင် Link များ ပို့ခွင့်မရှိပါ။", parse_mode="Markdown")
                    return
                except Exception:
                    pass

        # 2. GROUP ADMIN COMMANDS
        if text.startswith('/pin'):
            if is_group_admin(message.chat.id, message.from_user.id) and message.reply_to_message:
                try:
                    bot.pin_chat_message(message.chat.id, message.reply_to_message.message_id)
                    bot.reply_to(message, "📌 Message ကို Pin ထိုးလိုက်ပါပြီ။")
                except Exception as e:
                    bot.reply_to(message, f"❌ Pin ထိုးမရပါ: Bot ကို Admin 권한 ပေးထားပါသလား။")
            return

        elif text.startswith('/unpin'):
            if is_group_admin(message.chat.id, message.from_user.id):
                try:
                    bot.unpin_chat_message(message.chat.id)
                    bot.reply_to(message, "📌 Pin ဖြုတ်လိုက်ပါပြီ။")
                except Exception:
                    pass
            return

        elif text.startswith('/mute'):
            if is_group_admin(message.chat.id, message.from_user.id) and message.reply_to_message:
                args = text.split()
                minutes = int(args[1]) if len(args) > 1 and args[1].isdigit() else 10
                until_time = int(time.time()) + (minutes * 60)
                try:
                    bot.restrict_chat_member(message.chat.id, message.reply_to_message.from_user.id, until_date=until_time, can_send_messages=False)
                    bot.reply_to(message, f"🔇 [{message.reply_to_message.from_user.first_name}](tg://user?id={message.reply_to_message.from_user.id}) အား {minutes} မိနစ် Mute လိုက်ပါပြီ။", parse_mode="Markdown")
                except Exception as e:
                    bot.reply_to(message, f"❌ Error: {e}")
            return

        elif text.startswith('/unmute'):
            if is_group_admin(message.chat.id, message.from_user.id) and message.reply_to_message:
                try:
                    bot.restrict_chat_member(
                        message.chat.id, 
                        message.reply_to_message.from_user.id, 
                        can_send_messages=True, 
                        can_send_media_messages=True, 
                        can_send_other_messages=True, 
                        can_add_web_page_previews=True
                    )
                    bot.reply_to(message, f"🔊 Mute ဖြုတ်ပေးလိုက်ပါပြီ။")
                except Exception as e:
                    bot.reply_to(message, f"❌ Error: {e}")
            return

        elif text.startswith('/ban') or text.startswith('/kick'):
            if is_group_admin(message.chat.id, message.from_user.id) and message.reply_to_message:
                try:
                    bot.ban_chat_member(message.chat.id, message.reply_to_message.from_user.id)
                    bot.reply_to(message, f"🚫 [{message.reply_to_message.from_user.first_name}](tg://user?id={message.reply_to_message.from_user.id}) အား Group မှ Ban လိုက်ပါပြီ။", parse_mode="Markdown")
                except Exception as e:
                    bot.reply_to(message, f"❌ Error: {e}")
            return

    # GENERAL COMMANDS
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
            bot.reply_to(message, "👋 မင်္ဂလာပါ! Group ထဲသို့ ဝင်ရောက်ထားပြီးသည့်အတွက် ကျေးဇူးတင်ပါသည်။")

    elif text.startswith('/help'):
        if not is_owner(message.from_user.id):
            return
        help_text = (
            "🛠 **Admin Control Panel**\n\n"
            "🟢 `/status` - Bot Online ဟုတ်မဟုတ် စစ်ရန်\n"
            "📊 `/stats` - သုံးစွဲသူနှင့် ဂျီပီ အရေအတွက်\n"
            "👥 `/groups` - ဂျီပီများ စာရင်းကြည့်ရန်\n"
            "📢 `/broadcast <စာ>` - ကြော်ငြာ ပို့ရန်\n\n"
            "👥 **Group Admin Commands (In Group):**\n"
            "📌 `/pin` - Message ကို Reply လုပ်ပြီး Pin ထိုးရန်\n"
            "📌 `/unpin` - Pin ဖြုတ်ရန်\n"
            "🔇 `/mute <မိနစ်>` - Reply လုပ်ထားသူအား Mute ရန်\n"
            "🔊 `/unmute` - Mute ဖြုတ်ရန်\n"
            "🚫 `/ban` သို့မဟုတ် `/kick` - Group မှ Ban ထုတ်ရန်"
        )
        bot.reply_to(message, help_text, parse_mode="Markdown")

print("Bot စတင်ပွင့်နေပါပြီ...")
bot.infinity_polling(skip_pending=True)
