import time
from motor.motor_asyncio import AsyncIOMotorClient
import config

class DatabaseManager:
    def __init__(self):
        self.client = AsyncIOMotorClient(config.MONGO_URI)
        self.db = self.client.card_bot_db
        self.users = self.db.users
        self.cards = self.db.cards
        self.inventories = self.db.inventories

    async def get_or_create_user(self, user_id: int, username: str):
        user = await self.users.find_one({"user_id": user_id})
        if not user:
            user_data = {
                "user_id": user_id,
                "username": username,
                "coins": 1000,
                "level": 1,
                "created_at": time.time()
            }
            await self.users.insert_one(user_data)
            return user_data
        return user

    async def add_coins(self, user_id: int, amount: int):
        await self.users.update_one(
            {"user_id": user_id},
            {"$inc": {"coins": amount}}
        )

db = DatabaseManager()
