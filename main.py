import telebot
import sqlite3
import time

# ==========================================
# CONFIGURATION
# ==========================================
BOT_TOKEN = "8886077155:AAET1U9CXGZtaiIBLYxAutzFKFe-BkQpVno"
OWNER_ID = 7974865879

bot = telebot.TeleBot(BOT_TOKEN)

# ==========================================
# DATABASE SETUP
# ==========================================
def init_db():
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    # Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            username TEXT
        )
    ''')
    # Groups Table (ထည့်သွင်းသူနှင့် အချက်အလက်များ သိမ်းရန်)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS groups (
            chat_id INTEGER PRIMARY KEY,
            title TEXT,
            added_by_id INTEGER,
            added_by_name TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def save_user(user):
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO users VALUES (?, ?, ?)', 
                   (user.id, user.first_name, user.username))
    conn.commit()
    conn.close()

def save_group(chat_id, title, added_by_id, added_by_name):
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO groups VALUES (?, ?, ?, ?)', 
                   (chat_id, title, added_by_id, added_by_name))
    conn.commit()
    conn.close()

def is_owner(user_id):
    return user_id == OWNER_ID

# ==========================================
# AUTOMATED TRACKING (အလိုအလျောက် စာရင်းမှတ်ခြင်း)
# ==========================================

# ဂျီပီထဲသို့ Bot ကို ထည့်လိုက်ချိန်တွင် အလိုအလျောက် သိမ်းဆည်းခြင်း
@bot.my_chat_member_handler()
def track_group_addition(my_chat_member):
    new_status = my_chat_member.new_chat_member.status
    chat = my_chat_member.chat
    user = my_chat_member.from_user

    if chat.type in ['group', 'supergroup'] and new_status in ['member', 'administrator']:
        user_fullname = f"{user.first_name or ''} {user.last_name or ''}".strip()
        if user.username:
            user_fullname += f" (@{user.username})"
        save_group(chat.id, chat.title, user.id, user_fullname)

# စာဝင်လာတိုင်း User နှင့် Group အချက်အလက်များကို Auto Update လုပ်ခြင်း
@bot.message_handler(func=lambda message: True, content_types=['text', 'photo', 'video', 'document', 'new_chat_members'])
def handle_all_messages(message):
    # 1. Private User အချက်အလက်
    if message.chat.type == 'private':
        save_user(message.from_user)

    # 2. Group အချက်အလက်
    elif message.chat.type in ['group', 'supergroup']:
        user_fullname = f"{message.from_user.first_name or ''} {message.from_user.last_name or ''}".strip()
        if message.from_user.username:
            user_fullname += f" (@{message.from_user.username})"
        
        conn = sqlite3.connect('bot_data.db')
        cursor = conn.cursor()
        cursor.execute('SELECT added_by_id FROM groups WHERE chat_id = ?', (message.chat.id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            save_group(message.chat.id, message.chat.title, message.from_user.id, user_fullname)

    text = message.text if message.text else ""

    # ==========================================
    # OWNER COMMANDS (Owner တစ်ဦးတည်းသာ သုံးနိုင်သည်)
    # ==========================================

    # 5. Owner ပဲ သုံးလို့ရအောင် ကန့်သတ်ထားခြင်း
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
            "👥 `/groups` - ဂျီပီ နာမည်များ၊ ထည့်သွင်းသူနှင့် အလိုအလျောက် စစ်ထားသော လူဦးရေ စာရင်း\n"
            "📢 `/broadcast <စာ>` - ကြော်ငြာ စာ/ပုံ/ဗီဒီယို ပို့ရန်"
        )
        bot.reply_to(message, help_text, parse_mode="Markdown")

    # 1. Bot အလုပ်လုပ်နေလား စစ်ဆေးခြင်း
    elif text.startswith('/status'):
        if not is_owner(message.from_user.id):
            return
        bot.reply_to(message, "✅ **Bot status:** Online (ပုံမှန် အလုပ်လုပ်နေပါသည်)")

    # 2. သုံးစွဲသူနှင့် ဂျီပီ စုစုပေါင်း အရေအတွက် ကြည့်ခြင်း
    elif text.startswith('/stats'):
        if not is_owner(message.from_user.id):
            return
        conn = sqlite3.connect('bot_data.db')
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users')
        u_count = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM groups')
        g_count = cursor.fetchone()[0]
        conn.close()

        bot.reply_to(message, f"📊 **Bot စာရင်းချုပ်**\n\n👤 အသုံးပြုသူ (Users): {u_count} ယောက်\n👥 ဂျီပီများ (Groups): {g_count} ခု", parse_mode="Markdown")

    # 2. ဂျီပီ နာမည်များ၊ ထည့်သွင်းသူနှင့် လူဦးရေကို အလိုအလျောက် စစ်ဆေးပြသခြင်း
    elif text.startswith('/groups'):
        if not is_owner(message.from_user.id):
            return

        conn = sqlite3.connect('bot_data.db')
        cursor = conn.cursor()
        cursor.execute('SELECT chat_id, title, added_by_name FROM groups')
        groups_data = cursor.fetchall()
        conn.close()

        if not groups_data:
            bot.reply_to(message, "ℹ️ Bot ထည့်ထားသော ဂျီပီ စာရင်း မရှိသေးပါ။")
            return

        report = "👥 **Bot ရောက်ရှိနေသော ဂျီပီများ စာရင်း**\n\n"
        for index, g in enumerate(groups_data, 1):
            chat_id, title, added_by = g[0], g[1], g[2]
            try:
                # Telegram API မှတစ်ဆင့် ဂျီပီ လူဦးရေကို အလိုအလျောက် စစ်ပေးခြင်း
                members_count = bot.get_chat_member_count(chat_id)
                member_str = f"{members_count} ယောက်"
            except Exception:
                member_str = "စစ်မရပါ (Bot ကို ဂျီပီမှ ဖယ်ထုတ်ထားနိုင်သည်)"

            report += f"{index}။ **{title}**\n"
            report += f"   - 👤 ထည့်သွင်းသူ: {added_by or 'မသိရပါ'}\n"
            report += f"   - 👨‍👩‍👧‍👦 ဂျီပီ လူဦးရေ: `{member_str}`\n\n"

        if len(report) > 4000:
            for x in range(0, len(report), 4000):
                bot.send_message(message.chat.id, report[x:x+4000], parse_mode="Markdown")
        else:
            bot.reply_to(message, report, parse_mode="Markdown")

    # 3 & 4. ကြော်ငြာ ပို့ရန်နှင့် ရောက်/မရောက် Report ရယူခြင်း
    elif text.startswith('/broadcast'):
        if not is_owner(message.from_user.id):
            return

        broadcast_text = text.replace('/broadcast', '').strip()
        if not broadcast_text and not message.photo and not message.video and not message.document:
            bot.reply_to(message, "⚠️ ကျေးဇူးပြု၍ ပို့ချင်သော ကြော်ငြာ စာသား သို့မဟုတ် ပုံ/ဗီဒီယို ထည့်သွင်းပါ။\nဥပမာ - `/broadcast မင်္ဂလာပါ`")
            return

        status_msg = bot.reply_to(message, "⏳ ကြော်ငြာများ စတင်ပေးပို့နေပါပြီ...")

        conn = sqlite3.connect('bot_data.db')
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users')
        users = cursor.fetchall()
        cursor.execute('SELECT chat_id FROM groups')
        groups = cursor.fetchall()
        conn.close()

        all_targets = [u[0] for u in users] + [g[0] for g in groups]
        success = 0
        failed = 0

        for chat_id in all_targets:
            try:
                # ပုံ ပါဝင်ပါက
                if message.photo:
                    photo_id = message.photo[-1].file_id
                    bot.send_photo(chat_id, photo_id, caption=broadcast_text)
                # ဗီဒီယို ပါဝင်ပါက
                elif message.video:
                    video_id = message.video.file_id
                    bot.send_video(chat_id, video_id, caption=broadcast_text)
                # စာသီးသန့်
                else:
                    bot.send_message(chat_id, broadcast_text)
                
                success += 1
                time.sleep(0.05) # Rate Limit မမိအောင် တားဆီးခြင်း
            except Exception:
                failed += 1

        # 4. ရောက်/မရောက် အစီရင်ခံစာ ပြသခြင်း
        report = (
            "📢 **ကြော်ငြာ ပို့ဆောင်မှု အစီရင်ခံစာ (Broadcast Report)**\n\n"
            f"🎯 စုစုပေါင်း ပို့လွှတ်သည့် နေရာ: {len(all_targets)}\n"
            f"✅ အောင်မြင်စွာ ရောက်ရှိ: {success}\n"
            f"❌ မရောက်ရှိ/Block ထားသည်: {failed}"
        )
        bot.edit_message_text(report, chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode="Markdown")

print("Bot စတင်ပွင့်နေပါပြီ...")
bot.infinity_polling(skip_pending=True)
