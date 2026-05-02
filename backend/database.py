import asyncio

from motor.motor_asyncio import AsyncIOMotorClient
from config import settings
from logger import setup_logger

logger = setup_logger(__name__)

client: AsyncIOMotorClient = None
db = None


async def connect_db():
    global client, db
    client = AsyncIOMotorClient(settings.MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client[settings.DB_NAME]
    try:
        await asyncio.wait_for(client.admin.command("ping"), timeout=5)
        logger.info(f"Connected to MongoDB: {settings.DB_NAME}")
    except Exception as e:
        error_message = str(e) or "Timed out during MongoDB ping"
        logger.warning(f"MongoDB unavailable during startup: {error_message}")
        db = None


async def disconnect_db():
    global client, db
    if client:
        client.close()
        logger.info("MongoDB connection closed")
    client = None
    db = None


def get_db():
    return db
