import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Config
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "123456789").split(",") if x.strip()]

# Database Config
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://user:pass@cluster.mongodb.net/cardbot")

# Game Mechanics Config
SPAWN_MESSAGE_LIMIT = int(os.getenv("SPAWN_MESSAGE_LIMIT", "100"))
PORT = int(os.getenv("PORT", "10000"))
