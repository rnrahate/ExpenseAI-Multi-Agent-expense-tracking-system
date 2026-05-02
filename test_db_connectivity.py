import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from urllib.parse import urlsplit, urlunsplit

async def test_connection():
    # Load env from backend/.env
    load_dotenv("backend/.env")
    
    mongo_uri = os.getenv("MONGO_URI")
    db_name = os.getenv("DB_NAME", "ExpenseAI")

    def redact_uri(uri: str | None) -> str:
        if not uri:
            return "<missing>"
        try:
            parsed = urlsplit(uri)
            if parsed.username or parsed.password:
                host = parsed.hostname or ""
                if parsed.port:
                    host = f"{host}:{parsed.port}"
                netloc = f"{parsed.username or '***'}:***@{host}"
                return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))
        except Exception:
            pass
        return uri
    
    print(f"Connecting to: {redact_uri(mongo_uri)}")
    client = AsyncIOMotorClient(mongo_uri, serverSelectionTimeoutMS=5000)
    db = client[db_name]
    
    try:
        # Check connection
        await asyncio.wait_for(client.admin.command('ping'), timeout=5)
        print("MongoDB connection successful.")
        
        # Test collection creation / check
        collections = await db.list_collection_names()
        print(f"Existing collections: {collections}")
        
        if "users" not in collections:
            print("Creating 'users' collection...")
            await db.create_collection("users")
            print("'users' collection created.")
        else:
            print("'users' collection already exists.")
            
        # Test insert dummy
        test_user = {"email": "test_connection@example.com", "first_name": "Test"}
        result = await db.users.insert_one(test_user)
        print(f"Inserted test document with ID: {result.inserted_id}")
        
        # Cleanup test
        await db.users.delete_one({"_id": result.inserted_id})
        print("Cleanup test document successful.")
        
    except Exception as e:
        error_message = str(e) or "Timed out during MongoDB ping"
        print(f"Connection failed: {error_message}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(test_connection())
