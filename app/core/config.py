#aqui iremos colocar as configurações do projeto, como por exemplo a url do banco de dados, chaves de api, etc.
#BaseSettings é uma classe do Pydantic usada para criar classes de configuração que carregam valores automaticamente de:
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str 
    secret_key: str 
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    model_config = SettingsConfigDict(env_file=".env")
#Cria um objeto settings com os valores definidos em Settings
settings = Settings()