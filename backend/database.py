from motor.motor_asyncio import AsyncIOMotorClient
from config import settings
from logger import setup_logger

logger = setup_logger(__name__)

client: AsyncIOMotorClient = None
db = None


async def connect_db():
    global client, db
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.DB_NAME]
    logger.info(f"Connected to MongoDB: {settings.DB_NAME}")


async def disconnect_db():
    global client
    if client:
        client.close()
        logger.info("MongoDB connection closed")


def get_db():
    return db
