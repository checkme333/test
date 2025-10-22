from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    aster_api_key: str = ""
    aster_api_secret: str = ""
    aster_base_url: str = "https://fapi.asterdex.com"
    mock_mode: bool = False
    
    risk_max_leverage: int = 2
    risk_max_daily_loss: float = -200
    risk_max_symbol_exposure: float = 5000
    slippage_bps: int = 10
    
    redis_url: str = "redis://redis:6379"
    database_url: str = "postgresql://user:pass@postgres:5432/trade"
    
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
