import threading
import telebot
from config import BOT_TOKEN, PORT
from handlers import register_handlers
from services import start_flask, start_night_mode_scheduler

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

register_handlers(bot)

threading.Thread(target=start_flask, args=(PORT,), daemon=True).start()
start_night_mode_scheduler(bot)

if __name__ == '__main__':
    print("🚀 Bot is running successfully...")
    bot.infinity_polling(skip_pending=True)
