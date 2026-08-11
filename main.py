import telebot
from handlers import register_all_handlers

# ⚠️ Thanthi Bot Token ထည့်ပါ
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_HERE"

bot = telebot.TeleBot(BOT_TOKEN)

# Register Handlers
register_all_handlers(bot)

if __name__ == "__main__":
    print("🚀 All-In-One DIGI & Group Help Bot Running...")
    bot.infinity_polling()
