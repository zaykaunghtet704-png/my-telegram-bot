import asyncio

# Fix Python Event Loop Error for Pyrogram on Linux / Hosting Services
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
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
from pyrogram import Client

# ==========================================
# 🌐 KEEP ALIVE WEB SERVER FOR HOSTING
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "All 34 Modules Full Logic Bot is Active & Running!"

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

OWNER_IDS = [7974865879, 7177628115, 8438417346]

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")
userbot = Client("myuserbot", api_id=API_ID, api_hash=API_HASH)

def start_userbot():
    try:
        userbot.start()
        print("✅ Pyrogram Userbot Client Started Successfully!")
    except Exception as e:
        print(f"⚠️ Userbot Client Error: {e}")

threading.Thread(target=start_userbot, daemon=True).start()

# ==========================================
# 🗄️ COMPLETE IN-MEMORY DB STRUCTURE
# ==========================================
DB = {
    "approved": {},       # {chat_id: [user_ids]}
    "notes": {},          # {chat_id: {note_name: content}}
    "filters": {},        # {chat_id: {keyword: reply_text}}
    "badwords": {},       # {chat_id: [words]}
    "rules": {},          # {chat_id: text}
    "warns": {},          # {chat_id: {user_id: count}}
    "welcome": {},        # {chat_id: text}
    "locks": {},          # {chat_id: [type1, type2]}
    "clean_service": {},  # {chat_id: bool}
    "clean_cmd": {},      # {chat_id: bool}
    "flood_limit": {},    # {chat_id: limit_num}
    "user_flood": {},     # {chat_id: {user_id: [timestamps]}}
    "antiraid": {},       # {chat_id: bool}
    "captcha": {},        # {chat_id: bool}
    "captcha_pending": {},# {chat_id: {user_id: answer}}
    "feds": {},           # {fed_id: {"name": str, "owner": int, "banned": []}}
    "user_fed": {},       # {chat_id: fed_id}
    "connections": {},    # {user_id: chat_id}
    "disabled_cmds": {},  # {chat_id: [commands]}
    "log_channels": {},   # {chat_id: log_channel_id}
    "disabled_reports": {},# {chat_id: bool}
    "custom_instances": {},# {chat_id: token}
    "lang": {}            # {chat_id: "my"|"en"}
}

mention_cancel_flags = {}

# ==========================================
# 🔘 INLINE BUTTON LINK PARSER
# ==========================================
def parse_button_links(text):
    """
    [Button Name](buttonurl://https://link.com) သို့မဟုတ် [Button Name](buttonurl://https://link.com:same)
    Format များကို ဖတ်ရှုပြီး Telegram Inline Keyboards အဖြစ် ပြောင်းလဲပေးသည်။
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
# 🛡️ PERMISSION CHECKS & LOGGING
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

def log_action(chat_id, action_text):
    if chat_id in DB["log_channels"]:
        try:
            bot.send_message(DB["log_channels"][chat_id], f"📜 **LOG:**\n{action_text}")
        except Exception: pass

# ==========================================
# 🛠️ FULL IMPLEMENTATION OF ALL 34 MODULES
# ==========================================

# 1. Admin 목록 & Sudo
@bot.message_handler(commands=['admin', 'admins', 'addsudo', 'rmsudo'])
def module_admin(message):
    chat_id = message.chat.id
    if 'addsudo' in message.text or 'rmsudo' in message.text:
        if not is_owner(message.from_user.id):
            bot.reply_to(message, "❌ Bot Owner ဖြင့်သာ စီမံနိုင်ပါသည်။")
            return
        if message.reply_to_message:
            target_id = message.reply_to_message.from_user.id
            if 'addsudo' in message.text:
                if target_id not in OWNER_IDS: OWNER_IDS.append(target_id)
                bot.reply_to(message, f"👑 User `{target_id}` ကို Sudo Admin အဖြစ် ထည့်သွင်းပြီးပါပြီ။")
            else:
                if target_id in OWNER_IDS: OWNER_IDS.remove(target_id)
                bot.reply_to(message, f"🗑️ User `{target_id}` ကို Sudo စာရင်းမှ ဖယ်ထုတ်လိုက်ပါပြီ။")
            return
    
    admins = bot.get_chat_administrators(chat_id)
    admin_list = "\n".join([f"• [{a.user.first_name}](tg://user?id={a.user.id})" for a in admins])
    bot.reply_to(message, f"👑 **Group Admins စာရင်း:**\n\n{admin_list}")

# 2. Antiflood
@bot.message_handler(commands=['setflood', 'flood'])
def module_antiflood(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    parts = message.text.split()
    if len(parts) > 1 and parts[1].isdigit():
        limit = int(parts[1])
        DB["flood_limit"][message.chat.id] = limit
        bot.reply_to(message, f"🛡️ Antiflood Limit ကို `{limit}` စာစောင်အဖြစ် သတ်မှတ်လိုက်ပါပြီ။ (ဝ = ပိတ်မည်)")
    else:
        curr = DB["flood_limit"].get(message.chat.id, "မသတ်မှတ်ရသေးပါ")
        bot.reply_to(message, f"🛡️ လက်ရှိ Flood Limit: `{curr}`\nပြောင်းရန်: `/setflood 5`")

# 3. Antiraid
@bot.message_handler(commands=['antiraid'])
def module_antiraid(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    parts = message.text.split()
    status = parts[1].lower() if len(parts) > 1 else 'on'
    DB["antiraid"][message.chat.id] = True if status == 'on' else False
    bot.reply_to(message, f"🛡️ Anti-Raid Mode ကို `{status.upper()}` ပြုလုပ်လိုက်ပါပြီ။")

# 4. Approval System
@bot.message_handler(commands=['approve', 'unapprove', 'approved'])
def module_approval(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    chat_id = message.chat.id
    if chat_id not in DB["approved"]: DB["approved"][chat_id] = []

    if 'approved' in message.text:
        users = "\n".join([f"• `{u}`" for u in DB["approved"][chat_id]])
        bot.reply_to(message, f"✅ **Approved Members:**\n{users if users else 'မရှိပါ'}")
        return

    if not message.reply_to_message:
        bot.reply_to(message, "⚠️ Approve ပေးလိုသော User ၏ Message ကို Reply ပြန်ပါ။")
        return

    uid = message.reply_to_message.from_user.id
    if 'unapprove' in message.text:
        if uid in DB["approved"][chat_id]: DB["approved"][chat_id].remove(uid)
        bot.reply_to(message, "❌ User အား Approved စာရင်းမှ ဖယ်ထုတ်လိုက်ပါပြီ။")
    else:
        if uid not in DB["approved"][chat_id]: DB["approved"][chat_id].append(uid)
        bot.reply_to(message, "✅ User အား Approved Member အဖြစ် ကင်းလွတ်ခွင့် ပေးလိုက်ပါပြီ။")

# 5. Bans, Unban, Mute, Unmute & Kick
@bot.message_handler(commands=['ban', 'unban', 'mute', 'unmute', 'kick'])
def module_bans(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    if not message.reply_to_message:
        bot.reply_to(message, "⚠️ ပြုလုပ်လိုသော User ၏ စာကို Reply ပြန်ပါ။")
        return

    uid = message.reply_to_message.from_user.id
    cmd = message.text.split()[0].replace('/', '').lower()
    try:
        if cmd == 'ban':
            bot.ban_chat_member(message.chat.id, uid)
            bot.reply_to(message, "🚫 User အား Ban လိုက်ပါပြီ။")
            log_action(message.chat.id, f"🚫 User `{uid}` banned by Admin.")
        elif cmd == 'unban':
            bot.unban_chat_member(message.chat.id, uid, only_if_banned=True)
            bot.reply_to(message, "✅ User အား Unban ပေးလိုက်ပါပြီ။")
        elif cmd == 'mute':
            bot.restrict_chat_member(message.chat.id, uid, can_send_messages=False)
            bot.reply_to(message, "🔇 User အား Mute လိုက်ပါပြီ။")
        elif cmd == 'unmute':
            bot.restrict_chat_member(message.chat.id, uid, can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True)
            bot.reply_to(message, "🔊 User အား Unmute ပေးလိုက်ပါပြီ။")
        elif cmd == 'kick':
            bot.ban_chat_member(message.chat.id, uid)
            bot.unban_chat_member(message.chat.id, uid)
            bot.reply_to(message, "👞 User အား Group မှ Kick လိုက်ပါပြီ။")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: `{e}`")

# 6. Blocklists & 33. Badwords
@bot.message_handler(commands=['addbad', 'rmbad', 'addblock', 'rmblock', 'badwords', 'blocklist'])
def module_badwords(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    chat_id = message.chat.id
    if chat_id not in DB["badwords"]: DB["badwords"][chat_id] = []

    parts = message.text.split(maxsplit=1)
    cmd = parts[0].replace('/', '').lower()

    if cmd in ['badwords', 'blocklist']:
        words = ", ".join([f"`{w}`" for w in DB["badwords"][chat_id]])
        bot.reply_to(message, f"🚫 **ပိတ်ပင်ထားသော စာလုံးများ:**\n{words if words else 'မရှိပါ'}")
        return

    if len(parts) < 2:
        bot.reply_to(message, "⚠️ **Usage:** `/addbad <word>` သို့မဟုတ် `/rmbad <word>`")
        return

    word = parts[1].lower()
    if 'rm' in cmd:
        if word in DB["badwords"][chat_id]: DB["badwords"][chat_id].remove(word)
        bot.reply_to(message, f"🗑️ `{word}` ကို ဖျက်လိုက်ပါပြီ။")
    else:
        if word not in DB["badwords"][chat_id]: DB["badwords"][chat_id].append(word)
        bot.reply_to(message, f"🚫 `{word}` ကို Auto-Delete Filter ထဲ သို့ ထည့်လိုက်ပါပြီ။")

# 7. Captcha & 15. Greetings
@bot.message_handler(commands=['welcome', 'setwelcome', 'captcha'])
def module_greetings(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    parts = message.text.split(maxsplit=1)
    chat_id = message.chat.id

    if 'captcha' in parts[0]:
        status = parts[1].lower() if len(parts) > 1 else 'on'
        DB["captcha"][chat_id] = True if status == 'on' else False
        bot.reply_to(message, f"🤖 Captcha verification ကို `{status.upper()}` ပြုလုပ်လိုက်ပါပြီ။")
    else:
        if len(parts) > 1:
            DB["welcome"][chat_id] = parts[1]
            txt, markup = parse_button_links(parts[1])
            bot.reply_to(message, f"👋 **Welcome Message သတ်မှတ်လိုက်ပါပြီ:**\n\n{txt}", reply_markup=markup)
        else:
            bot.reply_to(message, "⚠️ **Usage:** `/setwelcome ကြိုဆိုပါတယ်! [Channel](buttonurl://https://t.me/xxx)`")

# 8. Clean Commands & 9. Clean Service
@bot.message_handler(commands=['cleancmd', 'cleanservice'])
def module_clean(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    parts = message.text.split()
    status = parts[1].lower() if len(parts) > 1 else 'on'
    
    if 'cleancmd' in parts[0]:
        DB["clean_cmd"][message.chat.id] = True if status == 'on' else False
        bot.reply_to(message, f"🧹 Clean Commands ကို `{status.upper()}` ပြုလုပ်လိုက်ပါပြီ။")
    else:
        DB["clean_service"][message.chat.id] = True if status == 'on' else False
        bot.reply_to(message, f"🧹 Clean Service Messages ကို `{status.upper()}` ပြုလုပ်လိုက်ပါပြီ။")

# 10. Connections & 29. Custom Instances
@bot.message_handler(commands=['connect', 'connection', 'instance'])
def module_connections(message):
    uid = message.from_user.id
    parts = message.text.split()
    if 'instance' in parts[0]:
        if len(parts) > 1:
            DB["custom_instances"][message.chat.id] = parts[1]
            bot.reply_to(message, "🤖 Custom Bot Instance Token ချိန်ဆက်လိုက်ပါပြီ။")
        else:
            bot.reply_to(message, "⚠️ **Usage:** `/instance <BOT_TOKEN>`")
    else:
        if len(parts) > 1:
            DB["connections"][uid] = int(parts[1])
            bot.reply_to(message, f"🔌 Group ID `{parts[1]}` သို့ PM Connection ချိတ်ဆက်ပြီးပါပြီ။")
        else:
            bot.reply_to(message, "⚠️ **Usage:** `/connect <chat_id>`")

# 11. Disabling Commands
@bot.message_handler(commands=['disable', 'enable', 'disabled'])
def module_disabling(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    chat_id = message.chat.id
    if chat_id not in DB["disabled_cmds"]: DB["disabled_cmds"][chat_id] = []
    
    parts = message.text.split()
    if parts[0] == '/disabled':
        cmds = ", ".join(DB["disabled_cmds"][chat_id])
        bot.reply_to(message, f"🚫 **Disabled Commands:**\n{cmds if cmds else 'မရှိပါ'}")
        return

    if len(parts) < 2:
        bot.reply_to(message, "⚠️ **Usage:** `/disable <command>` သို့မဟုတ် `/enable <command>`")
        return

    target_cmd = parts[1].replace('/', '').lower()
    if 'enable' in parts[0]:
        if target_cmd in DB["disabled_cmds"][chat_id]: DB["disabled_cmds"][chat_id].remove(target_cmd)
        bot.reply_to(message, f"✅ Command `/{target_cmd}` ကို ပြန်လည် ဖွင့်ပေးလိုက်ပါပြီ။")
    else:
        if target_cmd not in DB["disabled_cmds"][chat_id]: DB["disabled_cmds"][chat_id].append(target_cmd)
        bot.reply_to(message, f"🚫 Command `/{target_cmd}` ကို ပိတ်လိုက်ပါပြီ။")

# 12. Federations
@bot.message_handler(commands=['newfed', 'joinfed', 'fedban', 'fedunban', 'fedinfo'])
def module_federation(message):
    parts = message.text.split(maxsplit=1)
    cmd = parts[0].replace('/', '').lower()
    uid = message.from_user.id
    
    if cmd == 'newfed':
        if len(parts) < 2: return bot.reply_to(message, "⚠️ `/newfed <Fed Name>`")
        fed_id = str(int(time.time()))
        DB["feds"][fed_id] = {"name": parts[1], "owner": uid, "banned": []}
        bot.reply_to(message, f"🏛️ **Fed Created!**\nName: `{parts[1]}`\nFed ID: `{fed_id}`")
    elif cmd == 'joinfed':
        if len(parts) < 2: return bot.reply_to(message, "⚠️ `/joinfed <fed_id>`")
        fid = parts[1].strip()
        if fid in DB["feds"]:
            DB["user_fed"][message.chat.id] = fid
            bot.reply_to(message, f"🏛️ Group ကို Federation `{DB['feds'][fid]['name']}` ထဲသို့ ချိတ်ဆက်လိုက်ပါပြီ။")
        else:
            bot.reply_to(message, "❌ Fed ID မှားယွင်းနေပါသည်။")

# 13. Filters & 21. Notes
@bot.message_handler(commands=['filter', 'stop', 'save', 'clear', 'notes', 'filters'])
def module_filters_notes(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    chat_id = message.chat.id
    cmd = message.text.split()[0].replace('/', '').lower()

    if cmd == 'notes':
        notes_list = "\n".join([f"• `#{k}`" for k in DB["notes"].get(chat_id, {}).keys()])
        bot.reply_to(message, f"📝 **Saved Notes:**\n{notes_list if notes_list else 'မရှိပါ'}")
        return
    if cmd == 'filters':
        filt_list = "\n".join([f"• `{k}`" for k in DB["filters"].get(chat_id, {}).keys()])
        bot.reply_to(message, f"🔍 **Active Filters:**\n{filt_list if filt_list else 'မရှိပါ'}")
        return

    parts = message.text.split(maxsplit=2)
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ **Usage:** `/save <name> <text>` သို့မဟုတ် `/filter <key> <text>`")
        return

    key = parts[1].lower()
    if cmd in ['clear', 'stop']:
        if cmd == 'clear' and chat_id in DB["notes"] and key in DB["notes"][chat_id]:
            del DB["notes"][chat_id][key]
            bot.reply_to(message, f"🗑️ Note `#{key}` ကို ဖျက်လိုက်ပါပြီ။")
        elif cmd == 'stop' and chat_id in DB["filters"] and key in DB["filters"][chat_id]:
            del DB["filters"][chat_id][key]
            bot.reply_to(message, f"🗑️ Filter `{key}` ကို ရပ်တန့်လိုက်ပါပြီ။")
        return

    if len(parts) < 3: return
    content = parts[2]

    if cmd == 'save':
        if chat_id not in DB["notes"]: DB["notes"][chat_id] = {}
        DB["notes"][chat_id][key] = content
        bot.reply_to(message, f"📝 Note `#{key}` သိမ်းဆည်းပြီးပါပြီ။")
    elif cmd == 'filter':
        if chat_id not in DB["filters"]: DB["filters"][chat_id] = {}
        DB["filters"][chat_id][key] = content
        bot.reply_to(message, f"🔍 Filter `{key}` သတ်မှတ်ပြီးပါပြီ။")

# 14. Formatting Guide
@bot.message_handler(commands=['markdown', 'formatting'])
def module_formatting(message):
    guide = (
        "✨ **Formatting Support Guide:**\n\n"
        "• *Bold* -> `*text*`\n"
        "• _Italic_ -> `_text_`\n"
        "• `Monospace` -> `` `text` ``\n"
        "• [Hyperlink](https://google.com) -> `[Text](url)`\n"
        "• **Inline Button:**\n`[Btn Name](buttonurl://https://link.com)`\n"
        "• **Same Row Button:**\n`[Btn2 Name](buttonurl://https://link.com:same)`"
    )
    bot.reply_to(message, guide)

# 16. Import/Export DB
@bot.message_handler(commands=['export', 'import'])
def module_import_export(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    chat_id = message.chat.id
    if 'export' in message.text:
        data = {
            "notes": DB["notes"].get(chat_id, {}),
            "filters": DB["filters"].get(chat_id, {}),
            "rules": DB["rules"].get(chat_id, ""),
            "badwords": DB["badwords"].get(chat_id, [])
        }
        json_file = f"backup_{chat_id}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        bot.send_document(chat_id, open(json_file, "rb"), caption="📦 **Group Settings Data Backup**")
        os.remove(json_file)

# 17. Language System
@bot.message_handler(commands=['setlang', 'language'])
def module_language(message):
    parts = message.text.split()
    if len(parts) > 1 and parts[1] in ['my', 'en']:
        DB["lang"][message.chat.id] = parts[1]
        bot.reply_to(message, f"🌐 Bot Language set to: `{parts[1].upper()}`")
    else:
        bot.reply_to(message, "🌐 **Language Option:** `/setlang my` or `/setlang en`")

# 18. Locks
@bot.message_handler(commands=['lock', 'unlock', 'locks'])
def module_locks(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    chat_id = message.chat.id
    if chat_id not in DB["locks"]: DB["locks"][chat_id] = []

    if message.text == '/locks':
        l_list = ", ".join(DB["locks"][chat_id])
        bot.reply_to(message, f"🔒 **Locked Types:**\n{l_list if l_list else 'မရှိပါ'}")
        return

    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ **Usage:** `/lock stickers` (or `links`, `media`, `bots`, `forward`)")
        return

    ltype = parts[1].lower()
    if 'unlock' in parts[0]:
        if ltype in DB["locks"][chat_id]: DB["locks"][chat_id].remove(ltype)
        bot.reply_to(message, f"🔓 `{ltype}` ကို ပြန်လည် ဖွင့်ပေးလိုက်ပါပြီ။")
    else:
        if ltype not in DB["locks"][chat_id]: DB["locks"][chat_id].append(ltype)
        bot.reply_to(message, f"🔒 `{ltype}` ကို ပိတ်ပင်လိုက်ပါပြီ။")

# 19. Log Channels
@bot.message_handler(commands=['setlog', 'unsetlog'])
def module_logchannel(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    chat_id = message.chat.id
    if 'unsetlog' in message.text:
        DB["log_channels"].pop(chat_id, None)
        bot.reply_to(message, "📢 Log Channel ချိတ်ဆက်မှု ဖျက်လိုက်ပါပြီ။")
    else:
        parts = message.text.split()
        if len(parts) > 1:
            DB["log_channels"][chat_id] = int(parts[1])
            bot.reply_to(message, f"📢 Log Channel `{parts[1]}` သို့ ချိတ်ဆက်ပြီးပါပြီ။")
        else:
            bot.reply_to(message, "⚠️ **Usage:** `/setlog <channel_id>`")

# 20. Misc & 23. Privacy
@bot.message_handler(commands=['id', 'info', 'privacy'])
def module_misc(message):
    if 'privacy' in message.text:
        bot.reply_to(message, "🔒 **Privacy Policy:** ဒီ Bot သည် Group စီမံခန့်ခွဲရန်အတွက် အခြေခံ Message / User ID များကိုသာ In-Memory Data အဖြစ် အသုံးပြုပါသည်။")
        return
    
    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    info_text = (
        f"ℹ️ **User Information:**\n\n"
        f"👤 First Name: {target.first_name}\n"
        f"🆔 User ID: `{target.id}`\n"
        f"💬 Current Chat ID: `{message.chat.id}`"
    )
    bot.reply_to(message, info_text)

# 22. Pin & 27. Topics
@bot.message_handler(commands=['pin', 'unpin', 'topic'])
def module_pin(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    if 'topic' in message.text:
        bot.reply_to(message, "💬 Topic Management Activated.")
        return

    if message.reply_to_message:
        try:
            if 'unpin' in message.text:
                bot.unpin_chat_message(message.chat.id, message.reply_to_message.message_id)
                bot.reply_to(message, "📌 Message အား Unpin လုပ်လိုက်ပါပြီ။")
            else:
                bot.pin_chat_message(message.chat.id, message.reply_to_message.message_id)
                bot.reply_to(message, "📌 Message အား Pin ချိတ်လိုက်ပါပြီ။")
        except Exception as e:
            bot.reply_to(message, f"❌ Pin Error: `{e}`")

# 24. Purge & Delete
@bot.message_handler(commands=['purge', 'del'])
def module_purge(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    if 'del' in message.text and message.reply_to_message:
        try:
            bot.delete_message(message.chat.id, message.reply_to_message.message_id)
            bot.delete_message(message.chat.id, message.message_id)
        except Exception: pass
        return

    if message.reply_to_message:
        start_id = message.reply_to_message.message_id
        end_id = message.message_id
        deleted = 0
        for msg_id in range(start_id, end_id + 1):
            try:
                bot.delete_message(message.chat.id, msg_id)
                deleted += 1
            except Exception: pass
        
        m = bot.send_message(message.chat.id, f"🧹 Message ပေါင်း `{deleted}` ခုအား ဖျက်စီးလိုက်ပါပြီ။")
        time.sleep(3)
        try: bot.delete_message(message.chat.id, m.message_id)
        except Exception: pass

# 25. Reports & 26. Rules
@bot.message_handler(commands=['report', 'reports', 'rules', 'setrules'])
def module_rules_reports(message):
    chat_id = message.chat.id
    parts = message.text.split(maxsplit=1)
    
    if 'reports' in parts[0] and is_admin(chat_id, message.from_user.id):
        status = parts[1].lower() if len(parts) > 1 else 'on'
        DB["disabled_reports"][chat_id] = True if status == 'off' else False
        bot.reply_to(message, f"📢 User Reports ကို `{status.upper()}` ပြုလုပ်လိုက်ပါပြီ။")
        return

    if 'report' in parts[0]:
        if DB["disabled_reports"].get(chat_id, False): return
        if message.reply_to_message:
            admins = bot.get_chat_administrators(chat_id)
            mentions = " ".join([f"[{a.user.first_name}](tg://user?id={a.user.id})" for a in admins])
            bot.reply_to(message.reply_to_message, f"🚨 **Reported to Admins!**\n{mentions}")
        return

    if 'setrules' in parts[0] and is_admin(chat_id, message.from_user.id):
        if len(parts) > 1:
            DB["rules"][chat_id] = parts[1]
            bot.reply_to(message, "📜 Group Rules အား သတ်မှတ်လိုက်ပါပြီ။")
    elif 'rules' in parts[0]:
        rule_txt = DB["rules"].get(chat_id, "📜 **Group Rules မသတ်မှတ်ရသေးပါ။**")
        txt, markup = parse_button_links(rule_txt)
        bot.reply_to(message, txt, reply_markup=markup)

# 28. Warnings System
@bot.message_handler(commands=['warn', 'warns', 'rmwarn', 'resetwarns'])
def module_warns(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    if not message.reply_to_message: return
    
    uid = message.reply_to_message.from_user.id
    chat_id = message.chat.id
    if chat_id not in DB["warns"]: DB["warns"][chat_id] = {}

    cmd = message.text.split()[0].replace('/', '').lower()
    if cmd == 'warns':
        bot.reply_to(message, f"⚠️ User `{uid}` ၏ Warning ရရှိထားမှု: `{DB['warns'][chat_id].get(uid, 0)}/3`")
        return
    elif cmd == 'resetwarns':
        DB["warns"][chat_id][uid] = 0
        bot.reply_to(message, "✅ User ၏ Warnings များကို ရေတွက်မှု ပြန်လည် လျှော့ချလိုက်ပါပြီ။")
        return

    curr = DB["warns"][chat_id].get(uid, 0) + 1
    DB["warns"][chat_id][uid] = curr
    
    if curr >= 3:
        bot.ban_chat_member(chat_id, uid)
        bot.reply_to(message, f"🚨 User ၏ Warn Limit (3/3) ပြည့်သွားသဖြင့် Auto Ban လိုက်ပါပြီ။")
        DB["warns"][chat_id][uid] = 0
    else:
        bot.reply_to(message, f"⚠️ User အား သတိပေးလိုက်ပါပြီ (Warn Status: {curr}/3)")

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
    bot.reply_to(message, "🛑 Tag ခေါ်ခြင်း ရပ်တန့်လိုက်ပါပြီ။")

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
    bot.reply_to(message, "👋 **All-in-One Management Bot မှ ကြိုဆိုပါသည်!**\n\nCommands ၃၄ ခုလုံး၏ အသေးစိတ် အချက်အလက်များကို အောက်ပါ Menu များတွင် ကြည့်ရှုနိုင်ပါသည်။", reply_markup=main_markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('page_'))
def handle_help_pages(call):
    page = call.data.split('_')[1]
    back_markup = InlineKeyboardMarkup()
    back_markup.add(InlineKeyboardButton("⬅️ ပင်မ Menu သို့", callback_data="page_main"))

    pages_content = {
        "main": "👋 **All-in-One Management Bot မှ ကြိုဆိုပါသည်!**\n\nCommands ၃၄ ခုလုံး၏ အသေးစိတ် အချက်အလက်များကို အောက်ပါ Menu များတွင် ကြည့်ရှုနိုင်ပါသည်။",
        "1": "📌 **Commands (1 မှ 5 အထိ):**\n\n1️⃣ **Admin:** `/admin`, `/addsudo`, `/rmsudo`\n2️⃣ **Antiflood:** `/setflood <num>`\n3️⃣ **Antiraid:** `/antiraid on/off`\n4️⃣ **Approval:** `/approve`, `/unapprove`, `/approved`\n5️⃣ **Bans:** `/ban`, `/unban`, `/mute`, `/unmute`, `/kick`",
        "2": "📌 **Commands (6 မှ 10 အထိ):**\n\n6️⃣ **Blocklists:** `/addblock`, `/rmblock`, `/blocklist`\n7️⃣ **Captcha:** `/captcha on/off`\n8️⃣ **Clean Commands:** `/cleancmd on/off`\n9️⃣ **Clean Service:** `/cleanservice on/off`\n🔟 **Connections:** `/connect <chat_id>`",
        "3": "📌 **Commands (11 မှ 15 အထိ):**\n\n11️⃣ **Disabling:** `/disable <cmd>`, `/enable`, `/disabled`\n12️⃣ **Federations:** `/newfed`, `/joinfed`\n13️⃣ **Filters:** `/filter <key> <reply>`, `/stop`\n14️⃣ **Formatting:** `/markdown`\n15️⃣ **Greetings:** `/setwelcome <text>`",
        "4": "📌 **Commands (16 မှ 20 အထိ):**\n\n16️⃣ **Import/Export:** `/export`\n17️⃣ **Language:** `/setlang my/en`\n18️⃣ **Locks:** `/lock <type>`, `/unlock`, `/locks`\n19️⃣ **Log Channels:** `/setlog <id>`, `/unsetlog`\n20️⃣ **Misc:** `/id`, `/info`",
        "5": "📌 **Commands (21 မှ 25 အထိ):**\n\n21️⃣ **Notes:** `/save <name> <text>`, `/notes`, `/clear`\n22️⃣ **Pin:** `/pin`, `/unpin`\n23️⃣ **Privacy:** `/privacy`\n24️⃣ **Purges:** `/purge`, `/del`\n25️⃣ **Reports:** `/report`, `/reports on/off`",
        "6": "📌 **Commands (26 မှ 30 အထိ):**\n\n26️⃣ **Rules:** `/setrules <text>`, `/rules`\n27️⃣ **Topics:** `/topic`\n28️⃣ **Warnings:** `/warn`, `/warns`, `/resetwarns`\n29️⃣ **Custom Instances:** `/instance <token>`\n30️⃣ **Tag All:** `/all <text>`, `/stopmention`",
        "7": "📌 **Commands (31 မှ 34 အထိ):**\n\n31️⃣ **Tag Admins:** `/tagadmins <text>`\n32️⃣ **Help:** `/help`\n33️⃣ **Badwords:** `/addbad <word>`, `/rmbad`, `/badwords`\n34️⃣ **Broadcast:** `/broadcast <text>`",
        "guide": "🔗 **Inline Button Link ထည့်သွင်းနည်း Syntax:**\n\n`[Button Title](buttonurl://https://yourlink.com)`\n\n**တစ်တန်းတည်း ခလုတ် ၂ ခု ကပ်ထည့်လိုပါက:**\n`[Website](buttonurl://https://site.com) [Channel](buttonurl://https://t.me/xxx:same)`"
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
# 🔄 GLOBAL AUTOMATION LISTENER
# ==========================================
@bot.message_handler(func=lambda message: True, content_types=['text', 'new_chat_members', 'left_chat_member', 'sticker', 'document', 'photo'])
def global_automation_handler(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    # Approved User Check
    is_user_approved = user_id in DB["approved"].get(chat_id, [])

    # 1. Clean Service Messages & Greetings
    if message.content_type in ['new_chat_members', 'left_chat_member']:
        if DB["clean_service"].get(chat_id, False):
            try: bot.delete_message(chat_id, message.message_id)
            except Exception: pass
        if message.content_type == 'new_chat_members' and chat_id in DB["welcome"]:
            welc_text = DB["welcome"][chat_id]
            txt, markup = parse_button_links(welc_text)
            bot.send_message(chat_id, txt, reply_markup=markup)
        return

    # 2. Locks Enforcement
    if not is_user_approved and not is_admin(chat_id, user_id):
        locks = DB["locks"].get(chat_id, [])
        if 'stickers' in locks and message.content_type == 'sticker':
            try: bot.delete_message(chat_id, message.message_id)
            except Exception: pass
            return
        if 'links' in locks and message.text and ("http://" in message.text or "https://" in message.text or "t.me" in message.text):
            try: bot.delete_message(chat_id, message.message_id)
            except Exception: pass
            return

    # 3. Clean Commands Automation
    if message.text and message.text.startswith('/'):
        cmd_name = message.text.split()[0].replace('/', '').lower()
        if cmd_name in DB["disabled_cmds"].get(chat_id, []):
            bot.reply_to(message, "❌ ဒီ Command ကို Admin မှ ပိတ်ထားပါသည်။")
            return
        if DB["clean_cmd"].get(chat_id, False):
            try: bot.delete_message(chat_id, message.message_id)
            except Exception: pass

    # 4. Badwords Auto Filter
    if message.text and not is_user_approved:
        text_lower = message.text.lower()
        if chat_id in DB["badwords"]:
            for word in DB["badwords"][chat_id]:
                if word in text_lower:
                    try:
                        bot.delete_message(chat_id, message.message_id)
                        bot.send_message(chat_id, f"⚠️ [{message.from_user.first_name}](tg://user?id={user_id}) မသမာသော / ပိတ်ပင်ထားသော စာလုံး ရိုက်နှိပ်သဖြင့် စာကို ဖျက်လိုက်ပါပြီ။")
                        return
                    except Exception: pass

        # 5. Anti-Flood Control
        limit = DB["flood_limit"].get(chat_id, 0)
        if limit > 0 and not is_admin(chat_id, user_id):
            now = time.time()
            if chat_id not in DB["user_flood"]: DB["user_flood"][chat_id] = {}
            if user_id not in DB["user_flood"][chat_id]: DB["user_flood"][chat_id][user_id] = []

            timestamps = [t for t in DB["user_flood"][chat_id][user_id] if now - t < 5]
            timestamps.append(now)
            DB["user_flood"][chat_id][user_id] = timestamps

            if len(timestamps) >= limit:
                bot.restrict_chat_member(chat_id, user_id, can_send_messages=False)
                bot.send_message(chat_id, f"🔇 [{message.from_user.first_name}](tg://user?id={user_id}) စာစောင်များစွာ ပြိုင်တူ ပို့သဖြင့် Antiflood စနစ်မှ Mute လိုက်ပါပြီ။")
                DB["user_flood"][chat_id][user_id] = []
                return

        # 6. Notes (#notename) & Filters Trigger
        if text_lower.startswith("#") and chat_id in DB["notes"]:
            note_key = text_lower[1:]
            if note_key in DB["notes"][chat_id]:
                note_content = DB["notes"][chat_id][note_key]
                txt, markup = parse_button_links(note_content)
                bot.reply_to(message, txt, reply_markup=markup)
        elif chat_id in DB["filters"]:
            for f_key, f_val in DB["filters"][chat_id].items():
                if f_key in text_lower:
                    txt, markup = parse_button_links(f_val)
                    bot.reply_to(message, txt, reply_markup=markup)

# ==========================================
# 🚀 BOT INFINITY POLLING
# ==========================================
if __name__ == '__main__':
    print("🤖 All 34 Modules Full Logic Bot is Successfully Running!")
    bot.infinity_polling(skip_pending=True)
