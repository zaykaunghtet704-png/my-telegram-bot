import logging
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters
)
import config
import handlers
from services import keep_alive

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    # Flask Health Check Service ကို Background တွင် စတင်ခြင်း
    keep_alive()
    
    # Application Build ပြုလုပ်ခြင်း
    application = Application.builder().token(config.BOT_TOKEN).build()

    # Handlers များ ထည့်သွင်းခြင်း
    application.add_handler(CommandHandler("start", handlers.start_handler))
    application.add_handler(CommandHandler("help", handlers.help_handler))
    application.add_handler(CommandHandler("sysinfo", handlers.sysinfo_handler))
    
    application.add_handler(CallbackQueryHandler(handlers.callback_query_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.message_spawn_listener))

    # Bot ကို စတင်ခြင်း
    logger.info("Starting Telegram Bot Engine...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
