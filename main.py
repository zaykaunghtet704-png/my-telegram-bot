import telebot
import psycopg2
import time
import threading

# ==========================================
# CONFIGURATION
# ==========================================
BOT_TOKEN = "8886077155:AAET1U9CXGZtaiIBLYxAutzFKFe-BkQpVno"
OWNER_ID = 7974865879
DATABASE_URL = "postgresql://postgres.fdfcifwziqrqqjimtqgm:zaykaunghtet704%23%40@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres"

bot = telebot.TeleBot(BOT_TOKEN)

# ==========================================
# SUPABASE DATABASE SETUP
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
    return user_id == OWNER_ID

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
# AUTOMATED TRACKING
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

@bot.message_handler(func=lambda message: True, content_types=['text', 'photo', 'video', 'document', 'new_chat_members'])
def handle_all_messages(message):
    if message.chat.type == 'private':
        save_user(message.from_user)

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

    text = message.text if message.text else ""

    # OWNER COMMANDS
    if text.startswith('/start'):
        if not is_owner(message.from_user.id):
            bot.reply_to(message, "⚠️ တောင်းပန်ပါတယ်။ ဒီ Bot ကို ပိုင်ရှင် (Owner) သာလျှင် အသုံးပြုခွင့်ရှိပါတယ်။")
            return
        bot.reply_to(message, "👋 မင်္ဂလာပါ Owner! ကြော်ငြာများ ပို့ရန်နှင့် စာရင်းများကြည့်ရန် /help ကို နှိပ်ပါ။")

    elif text.startswith('/help'):
        if not is_owner(message.from_user.id):
            return
        help_text = (
            "🛠 **Owner Control Panel**\n\n"
            "🟢 `/status` - Bot အလုပ်လုပ်နေလား စစ်ဆေးရန်\n"
            "📊 `/stats` - သုံးစွဲသူနှင့် ဂျီပီ စုစုပေါင်း အရေအတွက်\n"
            "👥 `/groups` - ဂျီပီများ၊ ထည့်သွင်းသူနှင့် လူဦးရေ စာရင်း\n"
            "🔍 `/checkgroups` - ဂျီပီများ အလုပ်လုပ် မလုပ် ကိုယ်တိုင် စစ်ဆေးရန်\n"
            "📢 `/broadcast <စာ>` - ကြော်ငြာ စာ/ပုံ/ဗီဒီယို ပို့ရန်"
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

            report = "👥 **Bot ရောက်ရှိနေသော ဂျီပီများ စာရင်း**\n\n"
            for index, g in enumerate(groups_data, 1):
                chat_id, title, added_by = g[0], g[1], g[2]
                try:
                    members_count = bot.get_chat_member_count(chat_id)
                    member_str = f"{members_count} ယောက်"
                except Exception:
                    member_str = "စစ်မရပါ (Bot ဖယ်ထုတ်ခံထားရနိုင်သည်)"

                report += f"{index}။ **{title}**\n"
                report += f"   - 👤 ထည့်သွင်းသူ: {added_by or 'မသိရပါ'}\n"
                report += f"   - 👨‍👩‍👧‍👦 ဂျီပီ လူဦးရေ: `{member_str}`\n\n"

            if len(report) > 4000:
                for x in range(0, len(report), 4000):
                    bot.send_message(message.chat.id, report[x:x+4000], parse_mode="Markdown")
            else:
                bot.reply_to(message, report, parse_mode="Markdown")
        except Exception as e:
            bot.reply_to(message, f"❌ Error: {e}")

    elif text.startswith('/broadcast'):
        if not is_owner(message.from_user.id):
            return

        broadcast_text = text.replace('/broadcast', '').strip()
        if not broadcast_text and not message.photo and not message.video and not message.document:
            bot.reply_to(message, "⚠️ ကျေးဇူးပြု၍ ပို့ချင်သော ကြော်ငြာ စာသား သို့မဟုတ် ပုံ/ဗီဒီယို ထည့်သွင်းပါ။\nဥပမာ - `/broadcast မင်္ဂလာပါ`")
            return

        status_msg = bot.reply_to(message, "⏳ ကြော်ငြာများ စတင်ပေးပို့နေပါပြီ...")

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT user_id FROM users')
            users = cursor.fetchall()
            cursor.execute('SELECT chat_id FROM groups')
            groups = cursor.fetchall()
            cursor.close()
            conn.close()

            all_targets = [u[0] for u in users] + [g[0] for g in groups]
            success = 0
            failed = 0

            for chat_id in all_targets:
                try:
                    if message.photo:
                        photo_id = message.photo[-1].file_id
                        bot.send_photo(chat_id, photo_id, caption=broadcast_text)
                    elif message.video:
                        video_id = message.video.file_id
                        bot.send_video(chat_id, video_id, caption=broadcast_text)
                    else:
                        bot.send_message(chat_id, broadcast_text)
                    
                    success += 1
                    time.sleep(0.05)
                except Exception:
                    failed += 1
                    delete_group(chat_id)

            report = (
                "📢 **ကြော်ငြာ ပို့ဆောင်မှု အစီရင်ခံစာ (Broadcast Report)**\n\n"
                f"🎯 စုစုပေါင်း ပို့လွှတ်သည့် နေရာ: {len(all_targets)}\n"
                f"✅ အောင်မြင်စွာ ရောက်ရှိ: {success}\n"
                f"❌ မရောက်ရှိ/Block ထားသည်: {failed}"
            )
            bot.edit_message_text(report, chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode="Markdown")
        except Exception as e:
            bot.reply_to(message, f"❌ Error: {e}")

print("Bot စတင်ပွင့်နေပါပြီ...")
bot.infinity_polling(skip_pending=True)
