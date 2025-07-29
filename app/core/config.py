from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    database_url: str = Field(..., env="DATABASE_URL")
    redis_url: Optional[str] = Field(None, env="REDIS_URL")
    
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(None, env="ANTHROPIC_API_KEY")
    local_llm_endpoint: Optional[str] = Field(None, env="LOCAL_LLM_ENDPOINT")
    private_cloud_endpoint: Optional[str] = Field(None, env="PRIVATE_CLOUD_ENDPOINT")
    private_cloud_api_key: Optional[str] = Field(None, env="PRIVATE_CLOUD_API_KEY")
    
    default_llm_provider: str = Field("openai", env="DEFAULT_LLM_PROVIDER")
    
    host: str = Field("0.0.0.0", env="HOST")
    port: int = Field(8000, env="PORT")
    reload: bool = Field(True, env="RELOAD")
    
    otel_exporter_otlp_endpoint: Optional[str] = Field(None, env="OTEL_EXPORTER_OTLP_ENDPOINT")
    otel_service_name: str = Field("llm-wrapper-service", env="OTEL_SERVICE_NAME")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()