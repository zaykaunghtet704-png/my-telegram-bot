import os
import asyncio
import logging
from flask import Flask
from threading import Thread
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# Logging Setup
logging.basicConfig(level=logging.INFO)

# ==============================================================================
# 🌐 KEEP-ALIVE WEB SERVER FOR RENDER
# ==============================================================================
web_app = Flask('')

@web_app.route('/')
def home():
    return "Group Control Bot is Online!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.daemon = True
    t.start()

# ==============================================================================
# ⚙️ CONFIGURATION & CLIENT SETUP
# ==============================================================================
API_ID = int(os.environ.get("API_ID", "31788996"))
API_HASH = os.environ.get("API_HASH", "0c6714a879b2b1abba75dc4526521ca8")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

app = Client("group_control_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

cancel_flags = {}

# ==============================================================================
# 🔘 INLINE BUTTONS & HELP TEXTS
# ==============================================================================
START_TEXT = "👋 **မင်္ဂလာပါ! Group Control Bot မှ ကြိုဆိုပါတယ်။**\n\nအောက်ပါ Button များကို နှိပ်၍ အမိန့်များကို ကြည့်ရှုနိုင်ပါသည်။"

MAIN_BUTTONS = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("👑 Admin/Sudo", callback_data="help_admin"),
        InlineKeyboardButton("📢 Tag/Mention", callback_data="help_tag")
    ],
    [
        InlineKeyboardButton("🚫 Badwords", callback_data="help_badwords"),
        InlineKeyboardButton("🎯 Filters", callback_data="help_filters")
    ],
    [
        InlineKeyboardButton("📝 Notes", callback_data="help_notes"),
        InlineKeyboardButton("⚠️ Warnings", callback_data="help_warns")
    ],
    [
        InlineKeyboardButton("👋 Welcome", callback_data="help_welcome"),
        InlineKeyboardButton("📌 Pin", callback_data="help_pin")
    ],
    [
        InlineKeyboardButton("🔇 Mute", callback_data="help_mute"),
        InlineKeyboardButton("🚫 Ban/Kick", callback_data="help_bankick")
    ],
    [
        InlineKeyboardButton("📢 Broadcast", callback_data="help_broadcast")
    ]
])

BACK_BUTTON = InlineKeyboardMarkup([
    [InlineKeyboardButton("⬅️ Back", callback_data="help_main")]
])

HELP_TEXTS = {
    "admin": "👑 **Admin / Sudo Commands:**\n\n• `/addsudo` - Sudo ထည့်ရန်\n• `/rmsudo` - Sudo ဖြုတ်ရန်\n• `/sudolist` - Sudo စာရင်းကြည့်ရန်",
    "tag": "📢 **Tag / Mention Commands:**\n\n• `/all [စာ]` သို့မဟုတ် `@all` - အဖွဲ့ဝင်များအားလုံးကို Tag ခေါ်ရန်\n• `/admins` - Admin များကို Tag ခေါ်ရန်\n• `/stopmention` - Tag ခေါ်နေခြင်းကို ရပ်ရန်",
    "badwords": "🚫 **Badwords Commands:**\n\n• `/addbad` - Badword သတ်မှတ်ရန်\n• `/rmbad` - Badword ဖြုတ်ရန်\n• `/badwords` - Badword စာရင်းကြည့်ရန်",
    "filters": "🎯 **Filters Commands:**\n\n• `/filter` - Auto reply ထည့်ရန်\n• `/stop` - Filter ဖြုတ်ရန်\n• `/filters` - Active filters စာရင်း",
    "notes": "📝 **Notes Commands:**\n\n• `/save` - Note မှတ်ရန်\n• `/get` - Note ခေါ်ကြည့်ရန်\n• `/clear` - Note ဖျက်ရန်",
    "warns": "⚠️ **Warnings Commands:**\n\n• `/warn` - User အား သတိပေးရန်\n• `/rmwarn` - Warn ၁ ကြိမ် လျှော့ရန်\n• `/warns` - Warn အရေအတွက် ကြည့်ရန်",
    "welcome": "👋 **Welcome Commands:**\n\n• `/setwelcome` - Member သစ်ဝင်လျှင် ကြိုဆိုစာ သတ်မှတ်ရန်",
    "pin": "📌 **Pin Commands:**\n\n• `/pin` - Message အား Pin ထိန်းရန်\n• `/unpin` - Pin ဖြုတ်ရန်",
    "mute": "🔇 **Mute Commands:**\n\n• `/mute` - စာရေးခွင့် ပိတ်ရန်\n• `/unmute` - စာရေးခွင့် ပြန်ဖွင့်ပေးရန်",
    "bankick": "🚫 **Ban / Kick Commands:**\n\n• `/ban` - Group မှ Ban ရန်\n• `/unban` - Ban ဖြုတ်ရန်\n• `/kick` - Group မှ ထုတ်ရန်",
    "broadcast": "📢 **Broadcast Commands:**\n\n• `/broadcast` - Bot ရောက်နေသော Group အားလုံးသို့ စာပို့ရန်"
}

# ==============================================================================
# 🎯 HANDLERS & COMMANDS
# ==============================================================================
@app.on_message(filters.command("start"))
async def start_cmd(client: Client, message: Message):
    await message.reply_text(START_TEXT, reply_markup=MAIN_BUTTONS)

@app.on_callback_query(filters.regex("^help_"))
async def help_callback(client: Client, callback_query: CallbackQuery):
    data = callback_query.data.replace("help_", "")
    if data == "main":
        await callback_query.message.edit_text(START_TEXT, reply_markup=MAIN_BUTTONS)
    elif data in HELP_TEXTS:
        await callback_query.message.edit_text(HELP_TEXTS[data], reply_markup=BACK_BUTTON)
    await callback_query.answer()

# Mention All Command
@app.on_message(filters.command(["all", "tagall"]) | filters.regex(r"^@all"))
async def tag_all(client: Client, message: Message):
    if message.chat.type not in [filters.ChatType.GROUP, filters.ChatType.SUPERGROUP]:
        return
        
    chat_id = message.chat.id
    cancel_flags[chat_id] = False
    
    custom_text = message.text.split(maxsplit=1)[1] if len(message.command) > 1 else "📢 အဖွဲ့ဝင်များအားလုံး သတိထားရန်!"
    status_msg = await message.reply_text("📢 **Member အားလုံးအား Tag ခေါ်ယူနေပါသည်...**")
    
    mentions = []
    count = 0
    
    try:
        async for member in client.get_chat_members(chat_id):
            if cancel_flags.get(chat_id, False):
                await message.reply_text("🛑 Tag ခေါ်ယူခြင်းကို ရပ်တန့်လိုက်ပါပြီ။")
                return
                
            if not member.user.is_bot and not member.user.is_deleted:
                safe_name = (member.user.first_name or "User").replace("[", "").replace("]", "")
                mentions.append(f"[{safe_name}](tg://user?id={member.user.id})")
                count += 1
                
                if len(mentions) == 5:
                    await client.send_message(chat_id, f"📢 **{custom_text}**\n\n" + " ".join(mentions))
                    mentions = []
                    await asyncio.sleep(2)
                    
        if mentions and not cancel_flags.get(chat_id, False):
            await client.send_message(chat_id, f"📢 **{custom_text}**\n\n" + " ".join(mentions))
            
        await status_msg.delete()
        await message.reply_text(f"✅ စုစုပေါင်း Member `{count}` ယောက်အား Tag ခေါ်ယူပြီးပါပြီ။")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

@app.on_message(filters.command(["stopmention", "cancel"]))
async def stop_mention(client: Client, message: Message):
    cancel_flags[message.chat.id] = True
    await message.reply_text("🛑 Tag ခေါ်ယူခြင်းကို ရပ်တန့်လိုက်ပါပြီ။")

# ==============================================================================
# 🚀 MAIN RUNNER
# ==============================================================================
if __name__ == "__main__":
    keep_alive()
    print("Bot is starting...")
    app.run()
