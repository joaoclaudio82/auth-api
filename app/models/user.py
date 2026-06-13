#aqui temos 
#o modelo de dados do usuário, que define a estrutura da tabela "users" no banco de dados e as colunas que ela deve conter no caso aqui temos uma unica classe User, 
# que representa a tabela "users" no banco de dados. Ela herda da classe Base, que é a classe base para os modelos de banco de dados definida em app.core.database.
# A classe User define as colunas da tabela, como id, email, hashed_password, is_active e created_at, com seus respectivos tipos e restrições.

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# Define a classe User, que representa a tabela "users" no banco de dados.
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True) # Define a coluna "id" como a chave primária da tabela, do tipo inteiro e indexada para melhorar a performance das consultas.
    #os argumentos da função mapped_column definem as características da coluna no banco de dados, como tipo, restrições e índices, ou seja a estrutura da tabela e as regras de validação para os 
    # dados armazenados nela.

    email: Mapped[str] = mapped_column( # Define a coluna "email" como uma string de até 255 caracteres, única, indexada e não nula.
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    hashed_password: Mapped[str] = mapped_column( # Define a coluna "hashed_password" como uma string de até 255 caracteres e não nula.
        String(255),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column( # Define a coluna "is_active" como um valor booleano, com valor padrão True e não nula.
        Boolean,
        default=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column( # Define a coluna "created_at" como uma data e hora com fuso horário, com valor padrão sendo o momento atual e não nula.
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    
