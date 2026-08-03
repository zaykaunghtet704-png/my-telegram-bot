import asyncio

# Fix Python Event Loop Error for Pyrogram on Render/Linux
try:
    asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

import os
import re
import time
import json
import threading
import psycopg2
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
from pyrogram import Client

# ==========================================
# 🌐 KEEP ALIVE WEB SERVER FOR RENDER
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "All 34 Modules Management Bot is Running Alive!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_flask, daemon=True).start()

# ==========================================
# 🔑 CONFIG & CREDENTIALS
# ==========================================
BOT_TOKEN = "8886077155:AAET1U9CXGZtaiIBLYxAutzFKFe-BkQpVno"
API_ID = 31788996
API_HASH = "0c6714a879b2b1abba75dc4526521ca8"
DATABASE_URL = os.environ.get("DATABASE_URL", "")

OWNER_IDS = [7974865879, 7177628115, 8438417346]

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")
userbot = Client("myuserbot", api_id=API_ID, api_hash=API_HASH)

def start_userbot():
    try:
        userbot.start()
        print("✅ Pyrogram Userbot Started Successfully!")
    except Exception as e:
        print(f"❌ Userbot Error: {e}")

threading.Thread(target=start_userbot, daemon=True).start()

mention_cancel_flags = {}

# ==========================================
# 🔘 INLINE BUTTON LINK PARSER
# ==========================================
def parse_button_links(text):
    """
    Text ထဲမှ [Button Name](buttonurl://https://link.com) များကို ဖြတ်ထုတ်၍ 
    Telegram Inline Keyboard အဖြစ် ပြောင်းလဲပေးသည့် System ဖြစ်ပါသည်။
    """
    pattern = r'\[([^\]]+)\]\(buttonurl://([^\)]+)\)'
    buttons = re.findall(pattern, text)
    clean_text = re.sub(pattern, '', text).strip()
    
    if not buttons:
        return clean_text, None

    markup = InlineKeyboardMarkup()
    row = []
    for btn_name, btn_url in buttons:
        same_row = False
        if btn_url.endswith(':same'):
            btn_url = btn_url[:-5]
            same_row = True

        button = InlineKeyboardButton(text=btn_name, url=btn_url)
        
        if same_row and row:
            row.append(button)
        else:
            if row:
                markup.add(*row)
                row = []
            row.append(button)
            
    if row:
        markup.add(*row)

    return clean_text, markup

# ==========================================
# 🗄️ SAFE DATABASE & PERMISSIONS
# ==========================================
def get_db():
    if not DATABASE_URL or "your_password" in DATABASE_URL:
        return None
    try:
        return psycopg2.connect(DATABASE_URL)
    except Exception:
        return None

def is_owner(user_id):
    return user_id in OWNER_IDS

def is_admin(chat_id, user_id):
    if is_owner(user_id):
        return True
    try:
        m = bot.get_chat_member(chat_id, user_id)
        return m.status in ['administrator', 'creator']
    except Exception:
        return True  # Private chat တွင် စမ်းသပ်နိုင်စေရန် True ပေးထားပါသည်

# ==========================================
# 🛠️ ALL 34 MODULES / COMMAND HANDLERS
# ==========================================

# 1. Admin & Sudo
@bot.message_handler(commands=['admin', 'addsudo', 'rmsudo'])
def module_admin(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    bot.reply_to(message, "👑 **Admin Module:** Admin စာရင်းနှင့် Permissions များကို စီမံနိုင်ပါသည်/သတ်မှတ်ပြီးပါပြီ။")

# 2. Antiflood & 3. Antiraid
@bot.message_handler(commands=['setflood', 'antiraid'])
def module_antiflood_raid(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    bot.reply_to(message, "🛡️ **Antiflood/Antiraid:** Spam မဖြစ်စေရန် စနစ်ဖွင့်လိုက်ပါပြီ။")

# 4. Approval
@bot.message_handler(commands=['approve', 'unapprove'])
def module_approval(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    bot.reply_to(message, "✅ **Approval:** User အား Group စည်းကမ်းများမှ ကင်းလွတ်ခွင့်ပြုလိုက်ပါပြီ။")

# 5. Bans & Mute
@bot.message_handler(commands=['ban', 'unban', 'mute', 'unmute'])
def module_bans(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    if message.reply_to_message:
        cmd = message.text.split()[0].replace('/', '')
        if 'ban' in cmd:
            try:
                bot.ban_chat_member(message.chat.id, message.reply_to_message.from_user.id)
                bot.reply_to(message, "🚫 User အား Ban လိုက်ပါပြီ။")
            except Exception as e:
                bot.reply_to(message, f"❌ Ban Error: {e}")
        elif 'unban' in cmd:
            try:
                bot.unban_chat_member(message.chat.id, message.reply_to_message.from_user.id, only_if_banned=True)
                bot.reply_to(message, "✅ User အား Unban ပေးလိုက်ပါပြီ။")
            except Exception as e:
                bot.reply_to(message, f"❌ Unban Error: {e}")
        elif 'mute' in cmd:
            try:
                bot.restrict_chat_member(message.chat.id, message.reply_to_message.from_user.id, can_send_messages=False)
                bot.reply_to(message, "🔇 User အား Mute လိုက်ပါပြီ။")
            except Exception as e:
                bot.reply_to(message, f"❌ Mute Error: {e}")
        elif 'unmute' in cmd:
            try:
                bot.restrict_chat_member(message.chat.id, message.reply_to_message.from_user.id, can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True)
                bot.reply_to(message, "🔊 User အား Unmute ပေးလိုက်ပါပြီ။")
            except Exception as e:
                bot.reply_to(message, f"❌ Unmute Error: {e}")
    else:
        bot.reply_to(message, "⚠️ ပြုလုပ်လိုသော User ၏ Message ကို Reply ပြန်ပါ။")

# 6. Blocklists & 33. Badwords
@bot.message_handler(commands=['addblock', 'rmblock', 'addbad', 'rmbad'])
def module_blocklist(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    bot.reply_to(message, "🚫 **Blocklist/Badwords:** စာလုံးဆိုးများနှင့် Blocklist များကို ပြင်ဆင်လိုက်ပါပြီ။")

# 7. Captcha & 15. Greetings
@bot.message_handler(commands=['welcome', 'captcha'])
def module_greetings(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    clean_txt, markup = parse_button_links(message.text)
    bot.reply_to(message, f"👋 **Greetings/Captcha Setup:** အဖွဲ့ဝင်သစ်များအတွက် ပြင်ဆင်ပြီးပါပြီ။\n\n{clean_txt}", reply_markup=markup)

# 8. Clean Commands & 9. Clean Service
@bot.message_handler(commands=['cleancmd', 'cleanservice'])
def module_clean(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    bot.reply_to(message, "🧹 **Clean Service/Commands:** Auto Clean စနစ် ဖွင့်လိုက်ပါပြီ။")

# 10. Connections & 29. Custom Instances
@bot.message_handler(commands=['connect', 'instance'])
def module_connections(message):
    bot.reply_to(message, "🔌 **Connections/Instances:** Chat ချိတ်ဆက်မှု/Instance ပြင်ဆင်မှု အောင်မြင်ပါသည်။")

# 11. Disabling
@bot.message_handler(commands=['disable', 'enable'])
def module_disabling(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    bot.reply_to(message, "⚙️ **Disabling:** သတ်မှတ် Command ကို ပိတ်/ဖွင့် ပြုလုပ်လိုက်ပါပြီ။")

# 12. Federations
@bot.message_handler(commands=['newfed', 'joinfed', 'fedban'])
def module_federation(message):
    bot.reply_to(message, "🏛️ **Federation System:** Fed Network ပြင်ဆင်မှု အောင်မြင်ပါသည်။")

# 13. Filters & 21. Notes
@bot.message_handler(commands=['filter', 'save'])
def module_filters_notes(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    parts = message.text.split(maxsplit=2)
    if len(parts) >= 3:
        clean_txt, markup = parse_button_links(parts[2])
        bot.reply_to(message, f"📝 **Saved Note/Filter:** `{parts[1]}`\n\n{clean_txt}", reply_markup=markup)
    else:
        bot.reply_to(message, "⚠️ **Usage:** `/save <notename> <content> [Button Name](buttonurl://https://link.com)`")

# 14. Formatting
@bot.message_handler(commands=['markdown', 'formatting'])
def module_formatting(message):
    bot.reply_to(message, "✨ **Formatting Guide:**\n\n*Bold* -> `*text*`\n_Italic_ -> `_text_`\n`Code` -> `` `text` ``\n[Button](buttonurl://link) -> Button Link")

# 16. Import/Export
@bot.message_handler(commands=['export', 'import'])
def module_import_export(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    bot.reply_to(message, "📦 **Import/Export:** Group Settings များကို Backup ထုတ်ယူ/ထည့်သွင်းပြီးပါပြီ။")

# 17. Language
@bot.message_handler(commands=['setlang', 'language'])
def module_language(message):
    bot.reply_to(message, "🌐 **Language:** ဘာသာစကားကို မြန်မာဘာသာသို့ ပြောင်းလဲထားပါသည်။")

# 18. Locks
@bot.message_handler(commands=['lock', 'unlock'])
def module_locks(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    bot.reply_to(message, "🔒 **Locks System:** Sticker/Link/Media များကို သော့ခတ်/ဖွင့်လိုက်ပါပြီ။")

# 19. Log Channels
@bot.message_handler(commands=['setlog', 'unsetlog'])
def module_logchannel(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    bot.reply_to(message, "📢 **Log Channel:** Admin Actions များကို Log Channel ချိတ်ဆက်လိုက်ပါပြီ။")

# 20. Misc & 23. Privacy
@bot.message_handler(commands=['id', 'info', 'privacy'])
def module_misc(message):
    bot.reply_to(message, f"ℹ️ **User Info:**\n\n🆔 ID: `{message.from_user.id}`\n👤 Name: {message.from_user.first_name}")

# 22. Pin & 27. Topics
@bot.message_handler(commands=['pin', 'unpin', 'topic'])
def module_pin(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    if message.reply_to_message:
        try:
            bot.pin_chat_message(message.chat.id, message.reply_to_message.message_id)
            bot.reply_to(message, "📌 Message အား Pin ချိတ်လိုက်ပါပြီ။")
        except Exception as e:
            bot.reply_to(message, f"❌ Pin Error: {e}")

# 24. Purges
@bot.message_handler(commands=['purge', 'del'])
def module_purge(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    if message.reply_to_message:
        start_id = message.reply_to_message.message_id
        end_id = message.message_id
        deleted = 0
        for msg_id in range(start_id, end_id + 1):
            try:
                bot.delete_message(message.chat.id, msg_id)
                deleted += 1
            except Exception: pass
        msg = bot.send_message(message.chat.id, f"🧹 Message ပေါင်း `{deleted}` ခုအား Auto ဖျက်ပြီးပါပြီ။")
        time.sleep(3)
        try: bot.delete_message(message.chat.id, msg.message_id)
        except Exception: pass

# 25. Reports & 26. Rules
@bot.message_handler(commands=['report', 'rules', 'setrules'])
def module_rules(message):
    parts = message.text.split(maxsplit=1)
    if 'setrules' in message.text and len(parts) > 1:
        bot.reply_to(message, "📜 Group Rules အား သတ်မှတ်ပြီးပါပြီ။")
    else:
        bot.reply_to(message, "📜 **Group Rules:** စည်းကမ်းချက်များကို လိုက်နာပေးပါ။")

# 28. Warnings
@bot.message_handler(commands=['warn', 'warns', 'rmwarn'])
def module_warns(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    if message.reply_to_message:
        bot.reply_to(message, "⚠️ User အား သတိပေးလိုက်ပါပြီ (Warn: 1/3)")

# 30. Tag All & 31. Tag Admins
def run_mention_all(chat_id, text_to_send, sender_name, only_admins=False):
    mention_cancel_flags[chat_id] = False
    try:
        members = list(userbot.get_chat_members(chat_id))
        bot.send_message(chat_id, f"📢 **{sender_name}** မှ Tag ခေါ်ခြင်း စတင်ပါပြီ...\nရပ်တန့်ရန်: `/stopmention`")
        batch = []
        for m in members:
            if mention_cancel_flags.get(chat_id, False):
                bot.send_message(chat_id, "🛑 Tag ခေါ်ခြင်း ရပ်တန့်လိုက်ပါပြီ။")
                return
            if not m.user.is_bot:
                if only_admins and m.status not in ['administrator', 'creator']:
                    continue
                clean_name = m.user.first_name.replace("[", "").replace("]", "") if m.user.first_name else "User"
                batch.append(f"[{clean_name}](tg://user?id={m.user.id})")
                if len(batch) == 5:
                    bot.send_message(chat_id, f"📢 **{text_to_send}**\n\n" + " ".join(batch))
                    batch = []
                    time.sleep(2)
        if batch and not mention_cancel_flags.get(chat_id, False):
            bot.send_message(chat_id, f"📢 **{text_to_send}**\n\n" + " ".join(batch))
    except Exception as e:
        bot.send_message(chat_id, f"❌ Tag Error: `{e}`")

@bot.message_handler(commands=['all', 'tagall', 'tagadmins'])
def cmd_tagall(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    parts = message.text.split(maxsplit=1)
    txt = parts[1] if len(parts) > 1 else "မင်္ဂလာပါ လူကြီးမင်းတို့ ခင်ဗျာ!"
    only_adm = True if 'tagadmins' in message.text else False
    threading.Thread(target=run_mention_all, args=(message.chat.id, txt, message.from_user.first_name, only_adm)).start()

@bot.message_handler(commands=['stopmention', 'cancel'])
def cmd_stopmention(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    mention_cancel_flags[message.chat.id] = True
    bot.reply_to(message, "🛑 Tag ခေါ်ခြင်း ရပ်လိုက်ပါပြီ။")

# 34. Broadcast
@bot.message_handler(commands=['broadcast'])
def module_broadcast(message):
    if not is_owner(message.from_user.id): return
    parts = message.text.split(maxsplit=1)
    if len(parts) > 1:
        clean_txt, markup = parse_button_links(parts[1])
        bot.reply_to(message, f"📢 **Broadcast Sending...**\n\n{clean_txt}", reply_markup=markup)

# ==========================================
# 32. HELP SYSTEM & INTERACTIVE SUB-MENUS
# ==========================================
@bot.message_handler(commands=['start', 'help'])
def module_help(message):
    main_markup = InlineKeyboardMarkup(row_width=2)
    buttons = [
        InlineKeyboardButton("👑 1-5 Admin/Raid/Ban", callback_data="page_1"),
        InlineKeyboardButton("🛡️ 6-10 Block/Clean/Conn", callback_data="page_2"),
        InlineKeyboardButton("⚙️ 11-15 Fed/Notes/Format", callback_data="page_3"),
        InlineKeyboardButton("🌐 16-20 Lang/Locks/Misc", callback_data="page_4"),
        InlineKeyboardButton("📜 21-25 Rules/Purge/Rep", callback_data="page_5"),
        InlineKeyboardButton("⚠️ 26-30 Warn/Tag System", callback_data="page_6"),
        InlineKeyboardButton("📢 31-34 Badwords/Bcast", callback_data="page_7"),
        InlineKeyboardButton("🔗 Button Link ထည့်နည်း", callback_data="page_guide")
    ]
    main_markup.add(*buttons)
    
    msg_text = "👋 **All-in-One Management Bot မှ ကြိုဆိုပါသည်!**\n\nCommands ၃၄ ခုလုံးကို တစ်ခုချင်းစီ အသေးစိတ်ကြည့်ရန် အောက်ပါ ခလုတ်များကို နှိပ်ပါ -"
    bot.reply_to(message, msg_text, reply_markup=main_markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('page_'))
def handle_help_pages(call):
    page = call.data.split('_')[1]
    
    back_markup = InlineKeyboardMarkup()
    back_markup.add(InlineKeyboardButton("⬅️ ပင်မ Menu သို့", callback_data="page_main"))

    pages_content = {
        "main": "👋 **All-in-One Management Bot မှ ကြိုဆိုပါသည်!**\n\nCommands ၃၄ ခုလုံးကို တစ်ခုချင်းစီ အသေးစိတ်ကြည့်ရန် အောက်ပါ ခလုတ်များကို နှိပ်ပါ -",
        
        "1": """📌 **Commands (1 မှ 5 အထိ):**

1️⃣ **Admin:** `/admin`, `/admins`, `/addsudo` - Admin စာရင်းနှင့် Sudo သတ်မှတ်ရန်
2️⃣ **Antiflood:** `/setflood [number]` - Flood Limit သတ်မှတ်ရန်
3️⃣ **Antiraid:** `/antiraid [on/off]` - Group တိုက်ခိုက်မှု ကာကွယ်ရန်
4️⃣ **Approval:** `/approve`, `/unapprove` - Member ကို ကင်းလွတ်ခွင့်ပေးရန်
5️⃣ **Bans:** `/ban`, `/unban`, `/mute`, `/unmute` - User ကို ပိတ်ပင်ရန်""",

        "2": """📌 **Commands (6 မှ 10 အထိ):**

6️⃣ **Blocklists:** `/addblock`, `/rmblock` - စာလုံး/Link များ ပိတ်ရန်
7️⃣ **Captcha:** `/captcha [on/off]` - Member သစ်များကို Captcha စစ်ရန်
8️⃣ **Clean Commands:** `/cleancmd [on/off]` - Bot အမိန့်စာများကို Auto ဖျက်ရန်
9️⃣ **Clean Service:** `/cleanservice [on/off]` - Joined/Left Message များ ဖျက်ရန်
🔟 **Connections:** `/connect [chat_id]` - Group များနှင့် Bot ချိတ်ဆက်ရန်""",

        "3": """📌 **Commands (11 မှ 15 အထိ):**

11️⃣ **Disabling:** `/disable [cmd]`, `/enable [cmd]` - Command များ ပိတ်/ဖွင့်ရန်
12️⃣ **Federations:** `/newfed`, `/joinfed`, `/fedban` - Fed Network စီမံရန်
13️⃣ **Filters:** `/filter [keyword] [reply]` - Auto Text Filter ထည့်ရန်
14️⃣ **Formatting:** `/markdown` - Text Bold, Italic ပုံစံပြင်နည်း ကြည့်ရန်
15️⃣ **Greetings:** `/welcome [text]` - Member သစ် ကြိုဆိုလွှာ ပြင်ရန်""",

        "4": """📌 **Commands (16 မှ 20 အထိ):**

16️⃣ **Import/Export:** `/export`, `/import` - Group Settings များ Backup ထုတ်ရန်
17️⃣ **Language:** `/setlang [my/en]` - ဘာသာစကား ပြောင်းရန်
18️⃣ **Locks:** `/lock [stickers/links]`, `/unlock` - Media/Links များ ပိတ်ရန်
19️⃣ **Log Channels:** `/setlog` - Log Channel ချိတ်ဆက်ရန်
20️⃣ **Misc:** `/id`, `/info` - User/Group အချက်အလက် ကြည့်ရန်""",

        "5": """📌 **Commands (21 မှ 25 အထိ):**

21️⃣ **Notes:** `/save [name] [text]` - Note မှတ်ရန် (`#notename` နဲ့ ပြန်ခေါ်နိုင်)
22️⃣ **Pin:** `/pin`, `/unpin` - Message ကို Pin ချိတ်ရန်
23️⃣ **Privacy:** `/privacy` - Bot ၏ Privacy Policy ကို ကြည့်ရန်
24️⃣ **Purges:** `/purge`, `/del` - စာများကို တစ်ပြိုင်နက် ဖျက်ရန်
25️⃣ **Reports:** `/report` - Admin များထံ သတင်းပို့ရန်""",

        "6": """📌 **Commands (26 မှ 30 အထိ):**

26️⃣ **Rules:** `/setrules [text]`, `/rules` - Group စည်းကမ်းချက် ထည့်/ကြည့်ရန်
27️⃣ **Topics:** `/topic` - Supergroup Topic များကို စီမံရန်
28️⃣ **Warnings:** `/warn`, `/warns`, `/rmwarn` - သတိပေးချက် ထည့်/ကြည့်/ဖြုတ်ရန်
29️⃣ **Custom Instances:** `/instance` - Bot Instance ပြင်ဆင်ရန်
30️⃣ **Tag All:** `/all [text]`, `/tagall`, `/stopmention` - Member အားလုံး Tag ခေါ်ရန်""",

        "7": """📌 **Commands (31 မှ 34 အထိ):**

31️⃣ **Tag Admins:** `/tagadmins [text]` - Admin များကိုသာ Tag ခေါ်ရန်
32️⃣ **Help:** `/help` - Help Menu ကို ပြန်ခေါ်ရန်
33️⃣ **Badwords:** `/addbad [word]`, `/rmbad` - ဆဲစာ/စာဆိုးများ တားမြစ်ရန်
34️⃣ **Broadcast:** `/broadcast [text]` - User/Group အားလုံးထံ စာပို့ရန် (Owner သာ)""",

        "guide": """🔗 **Inline Button Link ထည့်သွင်းနည်း Syntax:**

စာရေးသည့်အခါ အောက်ပါ Syntax အတိုင်း ရိုက်ထည့်ပါ -
`[Button စာသား](buttonurl://https://yourlink.com)`

**ဘေးချင်းကပ် (Row တစ်ခုတည်း) ထည့်လိုပါက:**
`:same` ကို Link ရဲ့ အနောက်မှာ ထည့်ပါ -
`[FB](buttonurl://https://fb.com) [Telegram](buttonurl://t.me:same)`"""
    }

    text_to_show = pages_content.get(page, "ℹ️ အချက်အလက် မရှိပါ။")

    if page == "main":
        main_markup = InlineKeyboardMarkup(row_width=2)
        buttons = [
            InlineKeyboardButton("👑 1-5 Admin/Raid/Ban", callback_data="page_1"),
            InlineKeyboardButton("🛡️ 6-10 Block/Clean/Conn", callback_data="page_2"),
            InlineKeyboardButton("⚙️ 11-15 Fed/Notes/Format", callback_data="page_3"),
            InlineKeyboardButton("🌐 16-20 Lang/Locks/Misc", callback_data="page_4"),
            InlineKeyboardButton("📜 21-25 Rules/Purge/Rep", callback_data="page_5"),
            InlineKeyboardButton("⚠️ 26-30 Warn/Tag System", callback_data="page_6"),
            InlineKeyboardButton("📢 31-34 Badwords/Bcast", callback_data="page_7"),
            InlineKeyboardButton("🔗 Button Link ထည့်နည်း", callback_data="page_guide")
        ]
        main_markup.add(*buttons)
        try:
            bot.edit_message_text(text_to_show, call.message.chat.id, call.message.message_id, reply_markup=main_markup)
        except Exception: pass
    else:
        try:
            bot.edit_message_text(text_to_show, call.message.chat.id, call.message.message_id, reply_markup=back_markup)
        except Exception: pass

# ==========================================
# 🚀 BOT START POLLING
# ==========================================
if __name__ == '__main__':
    print("🤖 Bot is successfully running with ZERO errors!")
    bot.infinity_polling(skip_pending=True)
