import os
import telebot
from handlers import register_all_handlers

# Render Environment Variables မှ BOT_TOKEN ကို ဖတ်ယူခြင်း
# (Environment Variable မရှိပါက fallback အဖြစ် တိုက်ရိုက် ထည့်သွင်းထားသော Token ကို သုံးပါမည်)
BOT_TOKEN = os.getenv("BOT_TOKEN", "8886077155:AAET1U9CYG7tsjTRLVxAutz")

# Token ရှိ/မရှိ နှင့် ပုံစံ မှန်/မမှန် စစ်ဆေးခြင်း
if not BOT_TOKEN or ":" not in BOT_TOKEN:
    raise ValueError("Invalid BOT_TOKEN! Token must contain a colon (:).")

bot = telebot.TeleBot(BOT_TOKEN)

# Handlers များကို Register လုပ်ခြင်း
register_all_handlers(bot)

if __name__ == "__main__":
    print("🚀 DIGI Group Help Management Bot is running on Render...")
    bot.infinity_polling(skip_pending=True)
