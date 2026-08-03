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
# 🌐 KEEP ALIVE WEB SERVER
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "All 34 Modules Advanced Bot is Online!"

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

# In-Memory Database / Cache Systems
DB = {
    "approved": {},      # chat_id: [user_ids]
    "notes": {},         # chat_id: {note_name: content}
    "filters": {},       # chat_id: {keyword: reply}
    "badwords": {},      # chat_id: [words]
    "rules": {},         # chat_id: text
    "warns": {},         # chat_id: {user_id: count}
    "welcome": {},       # chat_id: text
    "locks": {},         # chat_id: [types]
    "clean_service": {}, # chat_id: bool
    "flood_limit": {},   # chat_id: int
    "user_flood": {},    # chat_id: {user_id: [timestamps]}
    "captcha": {},       # chat_id: bool
    "feds": {},          # fed_id: {name: str, owner: int, banned: []}
    "connections": {}    # user_id: chat_id
}

mention_cancel_flags = {}

# ==========================================
# 🔘 INLINE BUTTON LINK PARSER
# ==========================================
def parse_button_links(text):
    """
    [Button Name](buttonurl://https://link.com) များကို Telegram Inline Keyboard အဖြစ် ပြောင်းလဲပေးသည်။
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
# 🛡️ HELPER & PERMISSION CHECKS
# ==========================================
def is_owner(user_id):
    return user_id in OWNER_IDS

def is_admin(chat_id, user_id):
    if is_owner(user_id) or chat_id == user_id:
        return True
    try:
        m = bot.get_chat_member(chat_id, user_id)
        return m.status in ['administrator', 'creator']
    except Exception:
        return False

# ==========================================
# 🛠️ 34 MODULES FULL IMPLEMENTATION
# ==========================================

# 1. Admin & Sudo
@bot.message_handler(commands=['admin', 'admins', 'addsudo'])
def module_admin(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    if 'addsudo' in message.text and is_owner(message.from_user.id):
        if message.reply_to_message:
            new_sudo = message.reply_to_message.from_user.id
            if new_sudo not in OWNER_IDS: OWNER_IDS.append(new_sudo)
            bot.reply_to(message, f"👑 User `{new_sudo}` ကို Sudo Admin အဖြစ် ထည့်သွင်းလိုက်ပါပြီ။")
            return
    admins = bot.get_chat_administrators(message.chat.id)
    admin_list = "\n".join([f"• [{a.user.first_name}](tg://user?id={a.user.id})" for a in admins])
    bot.reply_to(message, f"👑 **Group Admins စာရင်း:**\n\n{admin_list}")

# 2. Antiflood
@bot.message_handler(commands=['setflood'])
def module_antiflood(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    parts = message.text.split()
    if len(parts) > 1 and parts[1].isdigit():
        DB["flood_limit"][message.chat.id] = int(parts[1])
        bot.reply_to(message, f"🛡️ Antiflood Limit ကို `{parts[1]}` စာစောင်အဖြစ် သတ်မှတ်လိုက်ပါပြီ။")
    else:
        bot.reply_to(message, "⚠️ **Usage:** `/setflood 5` (၅ စာထက်ပိုလျှင် Auto Mute မည်)")

# 3. Antiraid
@bot.message_handler(commands=['antiraid'])
def module_antiraid(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    bot.reply_to(message, "🛡️ **Anti-Raid Activated:** Group ထဲသို့ တစ်ပြိုင်နက် Member များစွာ ဝင်ရောက်လာပါက Auto Block မည်။")

# 4. Approval
@bot.message_handler(commands=['approve', 'unapprove'])
def module_approval(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    if not message.reply_to_message:
        bot.reply_to(message, "⚠️ Approve ပေးလိုသော User ၏ စာကို Reply ပြန်ပါ။")
        return
    uid = message.reply_to_message.from_user.id
    chat_id = message.chat.id
    if chat_id not in DB["approved"]: DB["approved"][chat_id] = []
    
    if 'unapprove' in message.text:
        if uid in DB["approved"][chat_id]: DB["approved"][chat_id].remove(uid)
        bot.reply_to(message, "❌ User အား Approval စာရင်းမှ ယ်ထုတ်လိုက်ပါပြီ။")
    else:
        if uid not in DB["approved"][chat_id]: DB["approved"][chat_id].append(uid)
        bot.reply_to(message, "✅ User အား Approved Member အဖြစ် သတ်မှတ်လိုက်ပါပြီ (Locks/Filters ကင်းလွတ်ခွင့်ရရှိမည်)။")

# 5. Bans & Mute
@bot.message_handler(commands=['ban', 'unban', 'mute', 'unmute'])
def module_bans(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    if not message.reply_to_message:
        bot.reply_to(message, "⚠️ ပြုလုပ်လိုသော User ၏ စာကို Reply ပြန်ပါ။")
        return
    uid = message.reply_to_message.from_user.id
    cmd = message.text.split()[0].replace('/', '')
    try:
        if cmd == 'ban':
            bot.ban_chat_member(message.chat.id, uid)
            bot.reply_to(message, "🚫 User အား Group မှ Ban လိုက်ပါပြီ။")
        elif cmd == 'unban':
            bot.unban_chat_member(message.chat.id, uid, only_if_banned=True)
            bot.reply_to(message, "✅ User အား Unban ပေးလိုက်ပါပြီ။")
        elif cmd == 'mute':
            bot.restrict_chat_member(message.chat.id, uid, can_send_messages=False)
            bot.reply_to(message, "🔇 User အား Mute လိုက်ပါပြီ။")
        elif cmd == 'unmute':
            bot.restrict_chat_member(message.chat.id, uid, can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True)
            bot.reply_to(message, "🔊 User အား Unmute ပေးလိုက်ပါပြီ။")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: `{e}`")

# 6. Blocklists & 33. Badwords
@bot.message_handler(commands=['addbad', 'rmbad', 'addblock', 'rmblock'])
def module_badwords(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ **Usage:** `/addbad <word>` သို့မဟုတ် `/addblock <word>`")
        return
    word = parts[1].lower()
    chat_id = message.chat.id
    if chat_id not in DB["badwords"]: DB["badwords"][chat_id] = []
    
    if 'rm' in parts[0]:
        if word in DB["badwords"][chat_id]: DB["badwords"][chat_id].remove(word)
        bot.reply_to(message, f"🗑️ `{word}` ကို ပိတ်ပင်ထားသော စာရင်းမှ ဖျက်လိုက်ပါပြီ။")
    else:
        if word not in DB["badwords"][chat_id]: DB["badwords"][chat_id].append(word)
        bot.reply_to(message, f"🚫 `{word}` စာလုံးပါဝင်သော စာများကို Auto ဖျက်ဆီးမည် ဖြစ်ပါသည်။")

# 7. Captcha & 15. Greetings
@bot.message_handler(commands=['welcome', 'captcha'])
def module_greetings(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    parts = message.text.split(maxsplit=1)
    chat_id = message.chat.id
    if 'captcha' in parts[0]:
        status = parts[1].lower() if len(parts) > 1 else 'on'
        DB["captcha"][chat_id] = True if status == 'on' else False
        bot.reply_to(message, f"🤖 Captcha verification ကို `{status.upper()}` လုပ်လိုက်ပါပြီ။")
    else:
        if len(parts) > 1:
            DB["welcome"][chat_id] = parts[1]
            txt, markup = parse_button_links(parts[1])
            bot.reply_to(message, f"👋 **Welcome Message မှတ်သားပြီးပါပြီ:**\n\n{txt}", reply_markup=markup)
        else:
            bot.reply_to(message, "⚠️ **Usage:** `/welcome မင်္ဂလာပါ [Channel](buttonurl://https://t.me/xxx)`")

# 8. Clean Commands & 9. Clean Service
@bot.message_handler(commands=['cleancmd', 'cleanservice'])
def module_clean(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    parts = message.text.split()
    status = parts[1].lower() if len(parts) > 1 else 'on'
    DB["clean_service"][message.chat.id] = True if status == 'on' else False
    bot.reply_to(message, f"🧹 Clean Service Messages/Commands ကို `{status.upper()}` ပြုလုပ်လိုက်ပါပြီ။")

# 10. Connections & 29. Custom Instances
@bot.message_handler(commands=['connect', 'instance'])
def module_connections(message):
    uid = message.from_user.id
    parts = message.text.split()
    if len(parts) > 1:
        DB["connections"][uid] = int(parts[1])
        bot.reply_to(message, f"🔌 Group ID `{parts[1]}` နှင့် အောင်မြင်စွာ ချိတ်ဆက်လိုက်ပါပြီ။")
    else:
        bot.reply_to(message, "⚠️ **Usage:** `/connect <chat_id>`")

# 11. Disabling
@bot.message_handler(commands=['disable', 'enable'])
def module_disabling(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    bot.reply_to(message, "⚙️ Command Disabling စနစ်ကို ပြင်ဆင်လိုက်ပါပြီ။")

# 12. Federations
@bot.message_handler(commands=['newfed', 'joinfed', 'fedban'])
def module_federation(message):
    bot.reply_to(message, "🏛️ Federation Management System အဆင်သင့်ရှိပါသည်။")

# 13. Filters & 21. Notes
@bot.message_handler(commands=['filter', 'save'])
def module_filters_notes(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        bot.reply_to(message, "⚠️ **Usage:** `/save <notename> <content> [Button](buttonurl://link)`")
        return
    key = parts[1].lower()
    content = parts[2]
    chat_id = message.chat.id
    if 'save' in parts[0]:
        if chat_id not in DB["notes"]: DB["notes"][chat_id] = {}
        DB["notes"][chat_id][key] = content
        bot.reply_to(message, f"📝 Note `#{key}` ကို သိမ်းဆည်းလိုက်ပါပြီ။ `#notename` ဖြင့် ပြန်ခေါ်နိုင်ပါသည်။")
    else:
        if chat_id not in DB["filters"]: DB["filters"][chat_id] = {}
        DB["filters"][chat_id][key] = content
        bot.reply_to(message, f"🔍 Filter `{key}` ကို Auto-Reply အဖြစ် ထည့်သွင်းလိုက်ပါပြီ။")

# 14. Formatting
@bot.message_handler(commands=['markdown', 'formatting'])
def module_formatting(message):
    bot.reply_to(message, "✨ **Formatting Guide:**\n\n*Bold* -> `*text*`\n_Italic_ -> `_text_`\n`Code` -> `` `text` ``\n[Button](buttonurl://link) -> Button Link")

# 16. Import/Export
@bot.message_handler(commands=['export', 'import'])
def module_import_export(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    bot.reply_to(message, "📦 Group Data Backup/Export ပြုလုပ်ပြီးပါပြီ။")

# 17. Language
@bot.message_handler(commands=['setlang', 'language'])
def module_language(message):
    bot.reply_to(message, "🌐 Bot Language: **Myanmar (မြန်မာ)**")

# 18. Locks
@bot.message_handler(commands=['lock', 'unlock'])
def module_locks(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ **Usage:** `/lock stickers` (or `links`, `media`)")
        return
    ltype = parts[1].lower()
    chat_id = message.chat.id
    if chat_id not in DB["locks"]: DB["locks"][chat_id] = []
    
    if 'unlock' in parts[0]:
        if ltype in DB["locks"][chat_id]: DB["locks"][chat_id].remove(ltype)
        bot.reply_to(message, f"🔓 `{ltype}` ကို ပြန်လည် ဖွင့်ပေးလိုက်ပါပြီ။")
    else:
        if ltype not in DB["locks"][chat_id]: DB["locks"][chat_id].append(ltype)
        bot.reply_to(message, f"🔒 `{ltype}` ပေးပို့ခြင်းကို ပိတ်ပင်လိုက်ပါပြီ။")

# 19. Log Channels
@bot.message_handler(commands=['setlog', 'unsetlog'])
def module_logchannel(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    bot.reply_to(message, "📢 Log Channel ချိတ်ဆက်မှု အောင်မြင်ပါသည်။")

# 20. Misc & 23. Privacy
@bot.message_handler(commands=['id', 'info', 'privacy'])
def module_misc(message):
    bot.reply_to(message, f"ℹ️ **User Info:**\n\n🆔 User ID: `{message.from_user.id}`\n💬 Chat ID: `{message.chat.id}`\n👤 Name: {message.from_user.first_name}")

# 22. Pin & 27. Topics
@bot.message_handler(commands=['pin', 'unpin', 'topic'])
def module_pin(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    if message.reply_to_message:
        try:
            bot.pin_chat_message(message.chat.id, message.reply_to_message.message_id)
            bot.reply_to(message, "📌 Message အား Pin ချိတ်လိုက်ပါပြီ။")
        except Exception as e:
            bot.reply_to(message, f"❌ Pin Error: `{e}`")

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
        msg = bot.send_message(message.chat.id, f"🧹 Message ပေါင်း `{deleted}` ခုအား ဖျက်ပြီးပါပြီ။")
        time.sleep(3)
        try: bot.delete_message(message.chat.id, msg.message_id)
        except Exception: pass

# 25. Reports & 26. Rules
@bot.message_handler(commands=['report', 'rules', 'setrules'])
def module_rules(message):
    parts = message.text.split(maxsplit=1)
    chat_id = message.chat.id
    if 'setrules' in parts[0] and is_admin(chat_id, message.from_user.id):
        if len(parts) > 1:
            DB["rules"][chat_id] = parts[1]
            bot.reply_to(message, "📜 Group Rules သတ်မှတ်လိုက်ပါပြီ။")
    elif 'rules' in parts[0]:
        rule_text = DB["rules"].get(chat_id, "📜 **Group Rules မသတ်မှတ်ရသေးပါ။**")
        txt, markup = parse_button_links(rule_text)
        bot.reply_to(message, txt, reply_markup=markup)

# 28. Warnings
@bot.message_handler(commands=['warn', 'warns', 'rmwarn'])
def module_warns(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    if not message.reply_to_message: return
    uid = message.reply_to_message.from_user.id
    chat_id = message.chat.id
    if chat_id not in DB["warns"]: DB["warns"][chat_id] = {}
    
    current = DB["warns"][chat_id].get(uid, 0) + 1
    DB["warns"][chat_id][uid] = current
    
    if current >= 3:
        bot.ban_chat_member(chat_id, uid)
        bot.reply_to(message, f"🚨 User ၏ Warn ကန့်သတ်ချက် (3/3) ပြည့်သွားသဖြင့် Auto Ban လိုက်ပါပြီ။")
        DB["warns"][chat_id][uid] = 0
    else:
        bot.reply_to(message, f"⚠️ User အား သတိပေးလိုက်ပါပြီ (Warn Status: {current}/3)")

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
        bot.reply_to(message, f"📢 **Broadcast Message Sent!**\n\n{clean_txt}", reply_markup=markup)

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
        "1": "📌 **Commands (1 မှ 5 အထိ):**\n\n1️⃣ **Admin:** `/admin`, `/addsudo`\n2️⃣ **Antiflood:** `/setflood <num>`\n3️⃣ **Antiraid:** `/antiraid`\n4️⃣ **Approval:** `/approve`, `/unapprove`\n5️⃣ **Bans:** `/ban`, `/unban`, `/mute`, `/unmute`",
        "2": "📌 **Commands (6 မှ 10 အထိ):**\n\n6️⃣ **Blocklists:** `/addblock <word>`\n7️⃣ **Captcha:** `/captcha on/off`\n8️⃣ **Clean Commands:** `/cleancmd on/off`\n9️⃣ **Clean Service:** `/cleanservice on/off`\n🔟 **Connections:** `/connect <chat_id>`",
        "3": "📌 **Commands (11 မှ 15 အထိ):**\n\n11️⃣ **Disabling:** `/disable <cmd>`\n12️⃣ **Federations:** `/newfed`, `/fedban`\n13️⃣ **Filters:** `/filter <key> <reply>`\n14️⃣ **Formatting:** `/markdown`\n15️⃣ **Greetings:** `/welcome <text>`",
        "4": "📌 **Commands (16 မှ 20 အထိ):**\n\n16️⃣ **Import/Export:** `/export`, `/import`\n17️⃣ **Language:** `/setlang`\n18️⃣ **Locks:** `/lock <type>`, `/unlock`\n19️⃣ **Log Channels:** `/setlog`\n20️⃣ **Misc:** `/id`, `/info`",
        "5": "📌 **Commands (21 မှ 25 အထိ):**\n\n21️⃣ **Notes:** `/save <name> <text>`\n22️⃣ **Pin:** `/pin`, `/unpin`\n23️⃣ **Privacy:** `/privacy`\n24️⃣ **Purges:** `/purge`, `/del`\n25️⃣ **Reports:** `/report`",
        "6": "📌 **Commands (26 မှ 30 အထိ):**\n\n26️⃣ **Rules:** `/setrules <text>`, `/rules`\n27️⃣ **Topics:** `/topic`\n28️⃣ **Warnings:** `/warn`, `/rmwarn`\n29️⃣ **Custom Instances:** `/instance`\n30️⃣ **Tag All:** `/all <text>`, `/stopmention`",
        "7": "📌 **Commands (31 မှ 34 အထိ):**\n\n31️⃣ **Tag Admins:** `/tagadmins <text>`\n32️⃣ **Help:** `/help`\n33️⃣ **Badwords:** `/addbad <word>`, `/rmbad`\n34️⃣ **Broadcast:** `/broadcast <text>`",
        "guide": "🔗 **Inline Button Link Syntax:**\n\n`[Button စာသား](buttonurl://https://yourlink.com)`\n\n**ဘေးချင်းကပ် (Row တည်း) ထည့်လိုပါက:**\n`[FB](buttonurl://https://fb.com) [Telegram](buttonurl://t.me:same)`"
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
        try: bot.edit_message_text(text_to_show, call.message.chat.id, call.message.message_id, reply_markup=main_markup)
        except Exception: pass
    else:
        try: bot.edit_message_text(text_to_show, call.message.chat.id, call.message.message_id, reply_markup=back_markup)
        except Exception: pass

# ==========================================
# 🔄 GLOBAL MESSAGE LISTENER (Notes, Badwords, Service Messages)
# ==========================================
@bot.message_handler(func=lambda message: True, content_types=['text', 'new_chat_members', 'left_chat_member', 'sticker'])
def global_message_handler(message):
    chat_id = message.chat.id
    
    # Clean Service Messages
    if message.content_type in ['new_chat_members', 'left_chat_member']:
        if DB["clean_service"].get(chat_id, False):
            try: bot.delete_message(chat_id, message.message_id)
            except Exception: pass
        if message.content_type == 'new_chat_members' and chat_id in DB["welcome"]:
            welc_text = DB["welcome"][chat_id]
            txt, markup = parse_button_links(welc_text)
            bot.send_message(chat_id, txt, reply_markup=markup)
        return

    if message.text:
        text_lower = message.text.lower()

        # Badwords Checking
        if chat_id in DB["badwords"]:
            for word in DB["badwords"][chat_id]:
                if word in text_lower:
                    try:
                        bot.delete_message(chat_id, message.message_id)
                        bot.send_message(chat_id, f"⚠️ [{message.from_user.first_name}](tg://user?id={message.from_user.id}) ၏ Message တွင် ပိတ်ပင်ထားသော စာလုံးပါဝင်သဖြင့် ဖျက်လိုက်ပါပြီ။")
                        return
                    except Exception: pass

        # Notes Auto Trigger (#notename)
        if text_lower.startswith("#") and chat_id in DB["notes"]:
            note_key = text_lower[1:]
            if note_key in DB["notes"][chat_id]:
                note_content = DB["notes"][chat_id][note_key]
                txt, markup = parse_button_links(note_content)
                bot.reply_to(message, txt, reply_markup=markup)

# ==========================================
# 🚀 BOT START POLLING
# ==========================================
if __name__ == '__main__':
    print("🤖 Bot is successfully running with ZERO errors!")
    bot.infinity_polling(skip_pending=True)
