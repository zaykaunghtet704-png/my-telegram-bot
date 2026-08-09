import os

# Telegram Bot Token (BotFather ထံမှ ရရှိသော Token)
BOT_TOKEN = os.getenv("BOT_TOKEN", "8886077155:AAET1U9CXGZtaiIBLYxAutzFKFe-BkQpVno")

# Bot Master Owners / Bot Admin များ၏ User ID များ
MASTER_OWNERS = [7974865879, 7177628115, 8438417346]

# Database File Name
DB_NAME = "group_bot_data.db"

# Web Server Port (Hosting Server များတွင် အသုံးပြုရန်)
PORT = int(os.environ.get("PORT", 8080))
