#aqui iremos colocar as configurações do projeto, como por exemplo a url do banco de dados, chaves de api, etc.
#BaseSettings é uma classe do Pydantic usada para criar classes de configuração que carregam valores automaticamente de:
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # database_url: obrigatória e não pode ser string vazia.
    database_url: str = Field(..., min_length=1)
    # secret_key: obrigatória e com pelo menos 32 caracteres (evita chave fraca/vazia).
    secret_key: str = Field(..., min_length=32)
    algorithm: str = "HS256"
    # access_token_expire_minutes: precisa ser maior que zero (token não pode expirar no passado).
    access_token_expire_minutes: int = Field(default=30, gt=0)
    model_config = SettingsConfigDict(env_file=".env")
#Cria um objeto settings com os valores definidos em Settings
settings = Settings()