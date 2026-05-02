from bson import ObjectId
from database import get_db
from exceptions import DatabaseUnavailableError
from logger import setup_logger

logger = setup_logger(__name__)


class DBService:
    def __init__(self):
        self.db = get_db()
        if self.db is None:
            raise DatabaseUnavailableError("Database is unavailable. Check MongoDB connectivity.")

    async def find_user_by_email(self, email: str):
        return await self.db.users.find_one({"email": email})

    async def find_user_by_phone(self, phone: str):
        return await self.db.users.find_one({"phone_number": phone})

    async def create_user(self, user_data: dict) -> ObjectId:
        result = await self.db.users.insert_one(user_data)
        logger.info(f"User created with id: {result.inserted_id}")
        return result.inserted_id

    async def save_analysis(self, user_id: str, analysis: dict):
        await self.db.analyses.insert_one({"user_id": user_id, **analysis})
