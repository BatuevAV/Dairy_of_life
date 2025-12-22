"""
Configuration management
"""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class Settings:
    """Application settings"""
    
    # Bot settings
    BOT_TOKEN: str = os.getenv('BOT_TOKEN', '')
    OWNER_TELEGRAM_ID: int = int(os.getenv('OWNER_TELEGRAM_ID', '0'))
    
    # Database settings
    DB_HOST: str = os.getenv('DB_HOST', 'localhost')
    DB_PORT: int = int(os.getenv('DB_PORT', '5432'))
    DB_USER: str = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD: str = os.getenv('DB_PASSWORD', 'postgres')
    DB_NAME: str = os.getenv('DB_NAME', 'dairy_of_life')
    
    # Timezone
    TIMEZONE: str = os.getenv('TIMEZONE', 'Asia/Bangkok')
    
    # Debug mode
    DEBUG: bool = os.getenv('DEBUG', 'False').lower() == 'true'
    
    @property
    def DATABASE_URL(self) -> str:
        """PostgreSQL async connection string"""
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    def validate(self):
        """Validate required settings"""
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN is required")
        if not self.OWNER_TELEGRAM_ID:
            raise ValueError("OWNER_TELEGRAM_ID is required")


# Create settings instance
settings = Settings()
