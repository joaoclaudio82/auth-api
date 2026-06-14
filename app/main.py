from fastapi import FastAPI

# importa o roteador de autenticação da API
from app.api import auth, users

# cria a aplicação FastAPI com título e versão
app = FastAPI(title="auth-api-fast", version="1.0.0")

# registra o roteador de autenticação em /auth
app.include_router(auth.router)

# registra o roteador de usuários em /users
# OBS: o objeto `user` precisa estar importado para que esta linha funcione
app.include_router(users.router)

# rota de saúde para verificar se a aplicação está rodando
@app.get("/health",tags=["infra"])
def health():
    return {"status": "ok"}

