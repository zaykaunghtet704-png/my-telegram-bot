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

# Owner နှင့် Co-Owner (Admin ID များ စာရင်း - ၃ ယောက်)
ADMIN_IDS = [7974865879, 7177628115, 8438417346]

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
    """ ADMIN_IDS စာရင်းထဲတွင် ပါဝင်ပါက Admin ဟု သတ်မှတ်မည် """
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
# 🔄 ANTI-SLEEP & AUTO-CHECK SYSTEM
# ==========================================

def keep_alive():
    while True:
        time.sleep(300)
        try:
            bot.get_me()
        except Exception:
            pass

threading.Thread(target=keep_alive, daemon=True).start()

def check_all_groups():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT chat_id, title FROM groups')
        groups = cursor.fetchall()
        cursor.close()
        conn.close()

        active_count = 0
        removed_count = 0

        for chat_id, title in groups:
            try:
                bot.get_chat(chat_id)
                active_count += 1
            except Exception:
                delete_group(chat_id)
                removed_count += 1

        return active_count, removed_count
    except Exception as e:
        print(f"Error checking groups: {e}")
        return 0, 0

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
# AUTOMATED TRACKING & GROUP HANDLERS
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
            bot.send_message(message.chat.id, f"👋 မင်္ဂလာပါ! **{message.chat.title}** ဂျီပီမှာ Bot ကို Admin အရာရှိအဖြစ် ခန့်အပ်ပေးပါရန်။", parse_mode="Markdown")
        else:
            welcome_text = f"👋 မင်္ဂလာပါ [{user.first_name}](tg://user?id={user.id})\n\n**{message.chat.title}** ဂျီပီမှ နွေးထွေးစွာ ကြိုဆိုပါတယ်။"
            bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown")

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
# 🛠 GROUP ADMIN COMMAND HANDLERS
# ==========================================

@bot.message_handler(commands=['pin'])
def cmd_pin(message):
    if message.chat.type in ['group', 'supergroup'] and is_group_admin(message.chat.id, message.from_user.id):
        if message.reply_to_message:
            try:
                bot.pin_chat_message(message.chat.id, message.reply_to_message.message_id)
                bot.reply_to(message, "📌 Message ကို Pin ထိုးလိုက်ပါပြီ။")
            except Exception:
                bot.reply_to(message, "❌ Pin ထိုးမရပါ: Bot ကို Admin 권한 ပေးထားပါသလား။")

@bot.message_handler(commands=['unpin'])
def cmd_unpin(message):
    if message.chat.type in ['group', 'supergroup'] and is_group_admin(message.chat.id, message.from_user.id):
        try:
            bot.unpin_chat_message(message.chat.id)
            bot.reply_to(message, "📌 Pin ဖြုတ်လိုက်ပါပြီ။")
        except Exception:
            pass

@bot.message_handler(commands=['mute'])
def cmd_mute(message):
    if message.chat.type in ['group', 'supergroup'] and is_group_admin(message.chat.id, message.from_user.id):
        if message.reply_to_message:
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
    if message.chat.type in ['group', 'supergroup'] and is_group_admin(message.chat.id, message.from_user.id):
        if message.reply_to_message:
            try:
                bot.restrict_chat_member(
                    message.chat.id, 
                    message.reply_to_message.from_user.id, 
                    can_send_messages=True, 
                    can_send_media_messages=True, 
                    can_send_other_messages=True, 
                    can_add_web_page_previews=True
                )
                bot.reply_to(message, "🔊 Mute ဖြုတ်ပေးလိုက်ပါပြီ။")
            except Exception as e:
                bot.reply_to(message, f"❌ Error: {e}")

@bot.message_handler(commands=['ban', 'kick'])
def cmd_ban(message):
    if message.chat.type in ['group', 'supergroup'] and is_group_admin(message.chat.id, message.from_user.id):
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
    text = message.text if message.text else ""
    text_to_check = message.text or message.caption or ""

    # PRIVATE CHAT LOGIC (လူတစ်ယောက်ချင်းစီ ပို့သော စာများ)
    if message.chat.type == 'private':
        save_user(message.from_user)

        # ADMIN/OWNER မဟုတ်သော သူများ၏ စာများကို ADMIN များထံ Forward ပို့ပေးခြင်း
        if not is_owner(message.from_user.id):
            user = message.from_user
            user_info = f"📩 **New Message Received!**\n\n👤 **From:** {user.first_name or ''} {user.last_name or ''}\n🆔 **User ID:** `{user.id}`\n🔗 **Username:** @{user.username or 'မရှိပါ'}\n\n💬 **Message:**"
            
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

        # Anti-Link Check for Non-Admins in Groups
        if not is_group_admin(message.chat.id, message.from_user.id):
            if contains_link(text_to_check):
                try:
                    bot.delete_message(message.chat.id, message.message_id)
                    bot.send_message(message.chat.id, f"⚠️ [{message.from_user.first_name}](tg://user?id={message.from_user.id}) ဂျီပီထဲတွင် Link သို့မဟုတ် Tag များ ပို့ခွင့်မရှိပါ။", parse_mode="Markdown")
                    return
                except Exception:
                    pass

    # BOT COMMANDS
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
            "🟢 `/status` - Bot အလုပ်လုပ်နေလား စစ်ဆေးရန်\n"
            "📊 `/stats` - သုံးစွဲသူနှင့် ဂျီပီ စုစုပေါင်း အရေအတွက်\n"
            "👥 `/groups` - ဂျီပီများ၊ ထည့်သွင်းသူနှင့် လူဦးရေ စာရင်း\n"
            "🔍 `/checkgroups` - ဂျီပီများ အလုပ်လုပ် မလုပ် ကိုယ်တိုင် စစ်ဆေးရန်\n"
            "📢 `/broadcast <စာ>` - ကြော်ငြာ စာ/ပုံ/ဗီဒီယို ပို့ရန်\n\n"
            "👥 **Group Admin Commands (In Group):**\n"
            "📌 `/pin` - Message ကို Reply လုပ်ပြီး Pin ထိုးရန်\n"
            "📌 `/unpin` - Pin ဖြုတ်ရန်\n"
            "🔇 `/mute <မိနစ်>` - Reply လုပ်ထားသူအား Mute ရန်\n"
            "🔊 `/unmute` - Mute ဖြုတ်ရန်\n"
            "🚫 `/ban` သို့မဟုတ် `/kick` - Group မှ Ban ထုတ်ရန်"
        )
        bot.reply_to(message, help_text, parse_mode="Markdown")

    elif text.startswith('/status'):
        if not is_owner(message.from_user.id):
            return
        bot.reply_to(message, "✅ **Bot status:** Online (မအိပ်ဘဲ အလုပ်လုပ်နေပါသည်)")

    elif text.startswith('/stats'):
        if not is_owner(message.from_user.id):
            return
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM users')
            u_count = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(*) FROM groups')
            g_count = cursor.fetchone()[0]
            cursor.close()
            conn.close()

            bot.reply_to(message, f"📊 **Bot စာရင်းချုပ်**\n\n👤 အသုံးပြုသူ (Users): {u_count} ယောက်\n👥 ဂျီပီများ (Groups): {g_count} ခု", parse_mode="Markdown")
        except Exception as e:
            bot.reply_to(message, f"❌ Error: {e}")

    elif text.startswith('/checkgroups'):
        if not is_owner(message.from_user.id):
            return
        
        status = bot.reply_to(message, "🔍 ဂျီပီများအားလုံးကို စစ်ဆေးနေပါသည်...")
        active, removed = check_all_groups()
        
        res = (
            "✅ **ဂျီပီများ စစ်ဆေးပြီးစီးပါပြီ**\n\n"
            f"💚 ပုံမှန် အလုပ်လုပ်နေသော ဂျီပီ: {active} ခု\n"
            f"❌ Bot ဖယ်ထုတ်ခံထားရ၍ စာရင်းမှ ရှင်းထုတ်လိုက်သော ဂျီပီ: {removed} ခု"
        )
        bot.edit_message_text(res, chat_id=message.chat.id, message_id=status.message_id, parse_mode="Markdown")

    elif text.startswith('/groups'):
        if not is_owner(message.from_user.id):
            return

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT chat_id, title, added_by_name FROM groups')
            groups_data = cursor.fetchall()
            cursor.close()
            conn.close()

            if not groups_data:
                bot.reply_to(message, "ℹ️ Bot ထည့်ထားသော ဂျီပီ စာရင်း မရှိသေးပါ။")
                return

            report = "👥 Bot ရောက်ရှိနေသော ဂျီပီများ စာရင်း\n\n"
            for index, g in enumerate(groups_data, 1):
                chat_id, title, added_by = g[0], g[1], g[2]
                try:
                    members_count = bot.get_chat_member_count(chat_id)
                    member_str = f"{members_count} ယောက်"
                except Exception:
                    member_str = "စစ်မရပါ (Bot ဖယ်ထုတ်ခံထားရနိုင်သည်)"

                report += f"{index}။ {title}\n"
                report += f"   - 👤 ထည့်သွင်းသူ: {added_by or 'မသိရပါ'}\n"
                report += f"   - 👨‍👩‍👧‍👦 ဂျီပီ လူဦးရေ: {member_str}\n\n"

            if len(report) > 4000:
                for x in range(0, len(report), 4000):
                    bot.send_message(message.chat.id, report[x:x+4000])
            else:
                bot.reply_to(message, report)
        except Exception as e:
            bot.reply_to(message, f"❌ Error: {e}")

    elif text.startswith('/broadcast'):
        if not is_owner(message.from_user.id):
            return

        broadcast_text = text.replace('/broadcast', '').strip()
        if not broadcast_text and not message.photo and not message.video and not message.document:
            bot.reply_to(message, "⚠️ ကျေးဇူးပြု၍ ပို့ချင်သော ကြော်ငြာ စာသား သို့မဟုတ် ပုံ/ဗီဒီယို ထည့်သွင်းပါ။\nဥပမာ - `/broadcast မင်္ဂလာပါ`", parse_mode="Markdown")
            return

        status_msg = bot.reply_to(message, "⏳ ကြော်ငြာများ စတင်ပေးပို့နေပါပြီ...")

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT user_id FROM users')
            users = [u[0] for u in cursor.fetchall()]
            
            cursor.execute('SELECT chat_id FROM groups')
            groups = [g[0] for g in cursor.fetchall()]
            cursor.close()
            conn.close()

            success = 0
            failed_users = 0
            failed_groups = 0

            # 1. BROADCAST TO USERS
            for user_id in users:
                try:
                    if message.photo:
                        photo_id = message.photo[-1].file_id
                        bot.send_photo(user_id, photo_id, caption=broadcast_text)
                    elif message.video:
                        video_id = message.video.file_id
                        bot.send_video(user_id, video_id, caption=broadcast_text)
                    else:
                        bot.send_message(user_id, broadcast_text)
                    
                    success += 1
                    time.sleep(0.05)
                except Exception:
                    failed_users += 1
                    delete_user(user_id)

            # 2. BROADCAST TO GROUPS
            for group_id in groups:
                try:
                    if message.photo:
                        photo_id = message.photo[-1].file_id
                        bot.send_photo(group_id, photo_id, caption=broadcast_text)
                    elif message.video:
                        video_id = message.video.file_id
                        bot.send_video(group_id, video_id, caption=broadcast_text)
                    else:
                        bot.send_message(group_id, broadcast_text)
                    
                    success += 1
                    time.sleep(0.05)
                except Exception:
                    failed_groups += 1
                    delete_group(group_id)

            total_targets = len(users) + len(groups)

            report = (
                "📢 **ကြော်ငြာ ပို့ဆောင်မှု အစီရင်ခံစာ (Broadcast Report)**\n\n"
                f"🎯 စုစုပေါင်း ပို့လွှတ်သည့် နေရာ: {total_targets}\n"
                f"✅ အောင်မြင်စွာ ရောက်ရှိ: {success}\n"
                f"❌ ပို့၍ မရသော User အရေအတွက်: {failed_users}\n"
                f"❌ ပို့၍ မရသော Group အရေအတွက်: {failed_groups}"
            )
            bot.edit_message_text(report, chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode="Markdown")
        except Exception as e:
            bot.reply_to(message, f"❌ Error: {e}")

print("Bot စတင်ပွင့်နေပါပြီ...")
bot.infinity_polling(skip_pending=True)
