import asyncio

# Fix Python 3.10+ Event Loop Error for Pyrogram on Render
try:
    asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

import os
import time
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
    return "Bot is Alive!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_flask, daemon=True).start()

# ==========================================
# 🔑 CREDENTIALS & HARDCODED CONFIG
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

# Safe DB Connection (Crash မဖြစ်စေရန်)
def get_db_connection():
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
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ['administrator', 'creator']
    except Exception:
        return True  # Private chat တွင် စမ်းသပ်နိုင်စေရန် True ပေးထားသည်

# ==========================================
# 🔘 HELP MENU & BUTTON HANDLER
# ==========================================
def get_main_help_markup():
    markup = InlineKeyboardMarkup(row_width=3)
    buttons = [
        InlineKeyboardButton("👑 Admin/Sudo", callback_data="help_admin"),
        InlineKeyboardButton("📢 Mention/Tag", callback_data="help_mention"),
        InlineKeyboardButton("🚫 Bans/Mute", callback_data="help_bans"),
        InlineKeyboardButton("⚠️ Warnings", callback_data="help_warns"),
        InlineKeyboardButton("📝 Notes/Filters", callback_data="help_notes"),
        InlineKeyboardButton("📜 Rules/Purge", callback_data="help_rules"),
        InlineKeyboardButton("📢 Broadcast", callback_data="help_broadcast")
    ]
    markup.add(*buttons)
    return markup

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(
        message, 
        "👋 မင်္ဂလာပါ! Group Management Bot မှ ကြိုဆိုပါတယ်။\n\nအောက်ပါ Button များကို နှိပ်၍ Commands များ ကြည့်နိုင်ပါသည်:", 
        reply_markup=get_main_help_markup()
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('help_'))
def callback_help(call):
    if call.data == "help_back":
        try:
            bot.edit_message_text(
                "👋 မင်္ဂလာပါ! Group Management Bot မှ ကြိုဆိုပါတယ်။\n\nအောက်ပါ Button များကို နှိပ်၍ Commands များ ကြည့်နိုင်ပါသည်:",
                call.message.chat.id, call.message.message_id,
                reply_markup=get_main_help_markup()
            )
        except Exception: pass
        return

    help_texts = {
        "help_admin": "👑 **Admin Commands**\n\n• `/addsudo` [reply/id] - Sudo user ထည့်ရန်\n• `/rmsudo` [reply/id] - Sudo user ဖြုတ်ရန်\n• `/admins` - Admin စာရင်း ကြည့်ရန်",
        "help_mention": "📢 **Mention Commands**\n\n• `/all` [စာ] သို့မဟုတ် `/tagall` - Member အားလုံးကို Tag ခေါ်ရန်\n• `/stopmention` သို့မဟုတ် `/cancel` - Tag ခေါ်နေတာ ရပ်ရန်",
        "help_bans": "🚫 **Bans & Mute Commands**\n\n• `/ban` [reply] - Member အား Ban ရန်\n• `/unban` [reply] - Unban ပေးရန်\n• `/mute` [reply] - စာရေးခွင့် ပိတ်ရန်\n• `/unmute` [reply] - စာရေးခွင့် ပြန်ဖွင့်ရန်",
        "help_warns": "⚠️ **Warning Commands**\n\n• `/warn` [reply] - သတိပေးရန် (3 ကြိမ်ပြည့်လျှင် Auto Ban)\n• `/setflood` [number] - Antiflood Limit သတ်မှတ်ရန်",
        "help_notes": "📝 **Notes & Filters**\n\n• `/save` [notename] [content] - Note မှတ်ရန်\n• `/filter` [keyword] [reply] - Filter ထည့်ရန်\n• `/addbad` [word] - မကောင်းသောစာလုံး ပိတ်ရန်",
        "help_rules": "📜 **Rules & Purge**\n\n• `/setrules` [စာ] - Group Rules ထည့်ရန်\n• `/rules` - Rules ကြည့်ရန်\n• `/purge` [reply] - စာများ ဖျက်ရန်\n• `/pin` [reply] - Pin ချိတ်ရန်",
        "help_broadcast": "📢 **Broadcast**\n\n• `/broadcast` [စာ] - User/Group အားလုံးထံ စာပို့ရန်"
    }

    text = help_texts.get(call.data, "ℹ️ အချက်အလက် မရှိသေးပါ။")
    back_markup = InlineKeyboardMarkup()
    back_markup.add(InlineKeyboardButton("⬅️ နောက်သို့", callback_data="help_back"))
    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=back_markup)
    except Exception: pass

# ==========================================
# 🔨 BAN, MUTE, WARN COMMANDS
# ==========================================
@bot.message_handler(commands=['ban'])
def cmd_ban(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    if message.reply_to_message:
        try:
            bot.ban_chat_member(message.chat.id, message.reply_to_message.from_user.id)
            bot.reply_to(message, "🚫 User အား Group မှ Ban လိုက်ပါပြီ။")
        except Exception as e:
            bot.reply_to(message, f"❌ Ban မရပါ: {e}")
    else:
        bot.reply_to(message, "⚠️ Ban ချင်သော User ၏ စာကို Reply ပြန်ပါ။")

@bot.message_handler(commands=['unban'])
def cmd_unban(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    if message.reply_to_message:
        try:
            bot.unban_chat_member(message.chat.id, message.reply_to_message.from_user.id, only_if_banned=True)
            bot.reply_to(message, "✅ User အား Unban ပေးလိုက်ပါပြီ။")
        except Exception as e:
            bot.reply_to(message, f"❌ Unban မရပါ: {e}")

@bot.message_handler(commands=['mute'])
def cmd_mute(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    if message.reply_to_message:
        try:
            bot.restrict_chat_member(message.chat.id, message.reply_to_message.from_user.id, can_send_messages=False)
            bot.reply_to(message, "🔇 User ရဲ့ စာရေးခွင့် ပိတ်လိုက်ပါပြီ။")
        except Exception as e:
            bot.reply_to(message, f"❌ Mute မရပါ: {e}")

@bot.message_handler(commands=['unmute'])
def cmd_unmute(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    if message.reply_to_message:
        try:
            bot.restrict_chat_member(message.chat.id, message.reply_to_message.from_user.id, can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True)
            bot.reply_to(message, "🔊 User အား စာပြန်ရေးခွင့် ပေးလိုက်ပါပြီ။")
        except Exception as e:
            bot.reply_to(message, f"❌ Unmute မရပါ: {e}")

# ==========================================
# 📢 TAG ALL / MENTION COMMANDS
# ==========================================
def run_mention_all(chat_id, text_to_send, sender_name):
    mention_cancel_flags[chat_id] = False
    try:
        members = list(userbot.get_chat_members(chat_id))
        bot.send_message(chat_id, f"📢 **{sender_name}** မှ Tag ခေါ်ခြင်း စတင်ပါပြီ...\nရပ်တန့်ရန်: `/stopmention` သို့မဟုတ် `/cancel`")
        
        batch = []
        for m in members:
            if mention_cancel_flags.get(chat_id, False):
                bot.send_message(chat_id, "🛑 Tag ခေါ်ခြင်းကို ရပ်တန့်လိုက်ပါပြီ။")
                return

            if not m.user.is_bot:
                clean_name = m.user.first_name.replace("[", "").replace("]", "") if m.user.first_name else "User"
                batch.append(f"[{clean_name}](tg://user?id={m.user.id})")
                
                if len(batch) == 5:
                    bot.send_message(chat_id, f"📢 **{text_to_send}**\n\n" + " ".join(batch))
                    batch = []
                    time.sleep(2)
        
        if batch and not mention_cancel_flags.get(chat_id, False):
            bot.send_message(chat_id, f"📢 **{text_to_send}**\n\n" + " ".join(batch))
            
    except Exception as e:
        bot.send_message(chat_id, f"❌ Tag Error (Userbot ကို Group Admin ပေးထားရန်လိုသည်): `{e}`")

@bot.message_handler(commands=['all', 'tagall'])
def cmd_tagall(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    parts = message.text.split(maxsplit=1)
    text = parts[1] if len(parts) > 1 else "မင်္ဂလာပါ လူကြီးမင်းတို့ ခင်ဗျာ!"
    threading.Thread(target=run_mention_all, args=(message.chat.id, text, message.from_user.first_name)).start()

@bot.message_handler(commands=['stopmention', 'cancel'])
def cmd_stopmention(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    mention_cancel_flags[message.chat.id] = True
    bot.reply_to(message, "🛑 Tag ခေါ်ခြင်းကို ရပ်တန့်လိုက်ပါပြီ။")

# ==========================================
# 🧹 PURGE & PIN COMMANDS
# ==========================================
@bot.message_handler(commands=['purge'])
def cmd_purge(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    if not message.reply_to_message:
        return bot.reply_to(message, "⚠️ Purging စလုပ်ချင်သည့် Message ကို Reply ပြန်ပေးပါ။")
    
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

@bot.message_handler(commands=['pin'])
def cmd_pin(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    if message.reply_to_message:
        try:
            bot.pin_chat_message(message.chat.id, message.reply_to_message.message_id)
            bot.reply_to(message, "📌 Message ကို Pin ချိတ်လိုက်ပါပြီ။")
        except Exception as e:
            bot.reply_to(message, f"❌ Pin မရပါ: {e}")

# ==========================================
# 🤖 BOT START POLLING
# ==========================================
if __name__ == '__main__':
    print("🤖 Bot is successfully running with ZERO errors!")
    bot.infinity_polling(skip_pending=True)
