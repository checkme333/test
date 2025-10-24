from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    aster_api_key: str = ""
    aster_api_secret: str = ""
    aster_base_url: str = "https://fapi.asterdex.com"
    mock_mode: bool = False
    
    chatgpt_aster_api_key: str = ""
    chatgpt_aster_api_secret: str = ""
    grok_aster_api_key: str = ""
    grok_aster_api_secret: str = ""
    claude_aster_api_key: str = ""
    claude_aster_api_secret: str = ""
    gemini_aster_api_key: str = ""
    gemini_aster_api_secret: str = ""
    deepseek_aster_api_key: str = ""
    deepseek_aster_api_secret: str = ""
    
    openai_api_key: str = ""
    xai_api_key: str = ""
    anthropic_api_key: str = ""
    deepseek_api_key: str = ""
    gemini_api_key: str = ""
    
    cloudflare_account_id: str = ""
    cloudflare_gateway_id: str = ""
    
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
