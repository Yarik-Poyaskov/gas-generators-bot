from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr, Field, field_validator
from typing import List, Any
import json

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )

    bot_token: SecretStr
    admin_ids: Any = Field(..., description="List of admin user IDs")
    monitored_trader_ids: Any = Field([], description="List of trader IDs to monitor in groups")
    trader_monitor_group_id: int = Field(None, description="Group ID where traders send schedules")
    group_id: int = Field(..., description="Group ID for sending reports")
    special_group_id: int = Field(None, description="Special Group ID for simplified reports")
    test_special_group_id: int = Field(None, description="Test Special Group ID for image reports")
    summary_report_time: str = Field("09:40", description="HH:MM for summary report")
    db_url: str = "sqlite+aiosqlite:///reports.db"
    tc_name: str = "Facility Name"
    users_per_page: int = 10

    # Web API settings
    api_port: int = 7895
    api_token: str = Field("your-secure-api-token", description="Token for API authorization")
    jwt_secret: SecretStr = SecretStr("change-me-in-production") # Can be overridden in .env
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 1440 # 24 hours

    # Web Push settings
    vapid_public_key: str = Field(None, description="VAPID Public Key for Web Push")
    vapid_private_key: str = Field(None, description="VAPID Private Key for Web Push")
    vapid_claim_email: str = Field("admin@tstt.eu", description="Admin email for VAPID claim")

    # Security settings
    cors_origins: str = Field("*", description="Comma-separated list of allowed CORS origins")

    # Google Sheets settings
    google_sheets_json_key: str = Field(None, description="Path to Google Service Account JSON key")
    google_sheets_url: str = Field(None, description="URL of the Google Spreadsheet")

    @field_validator('admin_ids', 'monitored_trader_ids', mode='before')
    @classmethod
    def assemble_ids(cls, v: Any) -> List[int]:
        if isinstance(v, str):
            try:
                if v.startswith('[') and v.endswith(']'):
                    return json.loads(v)
            except (ValueError, TypeError):
                pass
            return [int(x.strip()) for x in v.split(',') if x.strip()]
        return v

    @property
    def ADMIN_IDS_TUPLE(self) -> tuple[int, ...]:
        return tuple(self.admin_ids)

config = Settings()
