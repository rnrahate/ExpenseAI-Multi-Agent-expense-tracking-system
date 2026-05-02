import os
from pydantic_settings import BaseSettings, SettingsConfigDict

# Get the directory of the current file (backend/)
base_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(base_dir, ".env")

class Settings(BaseSettings):
    GEMINI_API_KEY: str
    MONGO_URI: str
    SECRET_KEY: str
    DB_NAME: str
    API_BASE_URL: str
    TOKEN_EXPIRE_HOURS: int = 2
    ALGORITHM: str = "HS256"

    model_config = SettingsConfigDict(env_file=env_path, env_file_encoding="utf-8", extra="ignore")


settings = Settings() #type:ignore
