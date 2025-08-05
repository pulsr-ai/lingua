from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    # Database configuration
    database_url: Optional[str] = Field(None, env="DATABASE_URL")
    db_host: str = Field("localhost", env="DB_HOST")
    db_port: int = Field(5432, env="DB_PORT")
    db_user: str = Field("postgres", env="DB_USER")
    db_password: str = Field("", env="DB_PASSWORD")
    db_name: str = Field("llm_wrapper", env="DB_NAME")
    
    redis_url: Optional[str] = Field(None, env="REDIS_URL")
    
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    openai_api_base_url: Optional[str] = Field(None, env="OPENAI_API_BASE_URL")
    anthropic_api_key: Optional[str] = Field(None, env="ANTHROPIC_API_KEY")
    local_llm_endpoint: Optional[str] = Field(None, env="LOCAL_LLM_ENDPOINT")
    private_cloud_endpoint: Optional[str] = Field(None, env="PRIVATE_CLOUD_ENDPOINT")
    private_cloud_api_key: Optional[str] = Field(None, env="PRIVATE_CLOUD_API_KEY")
    
    default_llm_provider: str = Field("openai", env="DEFAULT_LLM_PROVIDER")
    default_model: Optional[str] = None
    
    host: str = Field("0.0.0.0", env="HOST")
    port: int = Field(8000, env="PORT")
    reload: bool = Field(True, env="RELOAD")
    
    otel_exporter_otlp_endpoint: Optional[str] = Field(None, env="OTEL_EXPORTER_OTLP_ENDPOINT")
    otel_service_name: str = Field("llm-wrapper-service", env="OTEL_SERVICE_NAME")
    
    @validator('database_url', always=True)
    def build_database_url(cls, v, values):
        """Build database URL from components if not provided directly"""
        if v:
            return v
        
        db_host = values.get('db_host', 'localhost')
        db_port = values.get('db_port', 5432)
        db_user = values.get('db_user', 'postgres')
        db_password = values.get('db_password', '')
        db_name = values.get('db_name', 'llm_wrapper')
        
        password_part = f":{db_password}" if db_password else ""
        return f"postgresql://{db_user}{password_part}@{db_host}:{db_port}/{db_name}"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()