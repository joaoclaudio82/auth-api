from datetime import datetime

# Tipos de coluna e utilidades do SQLAlchemy
from sqlalchemy import Boolean, DateTime, String, func
# Mapped + mapped_column: a forma "moderna" (SQLAlchemy 2.0) de declarar colunas.
# Mapped[int] diz ao Python QUAL é o tipo do atributo; mapped_column descreve a COLUNA no banco.
from sqlalchemy.orm import Mapped, mapped_column

# Base é a classe declarativa que criamos em app/core/database.py.
# Todo modelo que herdar de Base vira uma tabela.
from app.core.database import Base


class User(Base):
    # __tablename__ define o nome da tabela no banco. Sem isso, o SQLAlchemy não sabe onde gravar.
    __tablename__ = "users"

    # Chave primária: identificador único de cada linha. index=True acelera buscas por id.
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # email: único (não pode haver dois usuários com o mesmo email) e indexado (login busca por email).
    # String(255) define o tamanho máximo da coluna no banco.
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)

    # NUNCA guardamos a senha pura. Aqui fica só o HASH gerado pelo passlib/bcrypt.
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # Permite "desativar" um usuário sem apagá-lo. default=True: já nasce ativo.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # server_default=func.now(): quem preenche a data é o PRÓPRIO banco, no momento do INSERT.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
