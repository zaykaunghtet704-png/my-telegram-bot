import psutil
from telegram import Update
from telegram.ext import ContextTypes
import config
import keyboards
from database import db

# Counter tracking in memory
message_counters = {}

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await db.get_or_create_user(user.id, user.username or user.first_name)
    
    caption = (
        f"👋 မင်္ဂလာပါ {user.first_name}!\n\n"
        "✨ **Enterprise Card Collector Bot** မှ ကြိုဆိုပါတယ်။\n"
        "ဂိမ်းကစားရန် နှင့် ကဒ်များ စုဆောင်းရန် အောက်ပါ Link များကို အသုံးပြုနိုင်ပါသည်။"
    )
    
    await update.message.reply_photo(
        photo="https://picsum.photos/800/400",
        caption=caption,
        reply_markup=keyboards.get_start_keyboard(),
        parse_mode="Markdown"
    )

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📜 **အသုံးပြုနိုင်သော Commands များ**\n\n"
        "🎮 **User Commands:**\n"
        "• `/claim` - ၁၂ နာရီ ၁ ကြိမ် အခမဲ့ ကဒ်ယူရန်\n"
        "• `/nclaim` - ၄ နာရီ ၁ ကြိမ် ၂ ကဒ် ယူရန်\n"
        "• `/inv` - မိမိ ပိုင်ဆိုင်သော ကဒ်များ ကြည့်ရန်\n"
        "• `/profile` - မိမိ အကောင့်အချက်အလက် ကြည့်ရန်\n\n"
        "⚙️ **Admin Commands:**\n"
        "• `/sysinfo` - Server Status (RAM/CPU) စစ်ဆေးရန်"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def sysinfo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in config.ADMIN_IDS:
        return
        
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    
    info = (
        "⚙️ **Render Server Status**\n\n"
        f"🖥 **CPU Usage:** {cpu}%\n"
        f"💾 **RAM Usage:** {ram}%\n"
        "🟢 **Status:** Operational"
    )
    await update.message.reply_text(info, parse_mode="Markdown")

async def message_spawn_listener(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or update.effective_chat.type == "private":
        return

    chat_id = update.effective_chat.id
    message_counters[chat_id] = message_counters.get(chat_id, 0) + 1

    if message_counters[chat_id] >= config.SPAWN_MESSAGE_LIMIT:
        message_counters[chat_id] = 0
        await context.bot.send_photo(
            chat_id=chat_id,
            photo="https://picsum.photos/400/600",
            caption="✨ **Rare Card တစ်ကဒ် ကျလာပါပြီ!**\nပထမဆုံး Grab နှိပ်သူ ရရှိပါမည်။",
            reply_markup=keyboards.get_spawn_keyboard(),
            parse_mode="Markdown"
        )

async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "claim_spawn_card":
        user = query.from_user
        await db.get_or_create_user(user.id, user.username or user.first_name)
        await query.edit_message_caption(
            caption=f"🎉 **{user.first_name}** မှ ကဒ်ကို ပထမဆုံး Grab ရရှိသွားပါသည်။!",
            parse_mode="Markdown"
        )
