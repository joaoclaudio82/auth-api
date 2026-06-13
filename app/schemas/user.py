from datetime import datetime

# BaseModel: classe base de todo schema Pydantic (valida e serializa dados).
# EmailStr: tipo que valida automaticamente se a string é um email de verdade.
# Field: permite adicionar regras a um campo (tamanho mínimo, etc.).
# ConfigDict: configura o comportamento do schema (usamos para ler direto do objeto do banco).
from pydantic import BaseModel, ConfigDict, EmailStr, Field


# UserBase: o que é COMUM a vários schemas. Evita repetir 'email' em todo lugar.
class UserBase(BaseModel):
    email: EmailStr


# UserCreate: o que o cliente ENVIA ao se cadastrar (POST /users).
# Tem 'password' em texto puro (que vamos transformar em hash antes de salvar).
# Repare: este schema tem 'password', mas o schema de resposta NÃO terá.
class UserCreate(UserBase):
    password: str = Field(min_length=8, description="Senha em texto puro, mínimo 8 caracteres")


# UserRead: o que a API DEVOLVE. Note que NÃO há 'password' nem 'hashed_password' aqui:
# é assim que garantimos não vazar a senha na resposta.
class UserRead(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    # from_attributes=True permite o Pydantic construir este schema a partir de um
    # objeto do SQLAlchemy (lendo user.id, user.email...) e não só de um dicionário.
    model_config = ConfigDict(from_attributes=True)
