from fastapi import FastAPI

# importa o roteador de autenticação da API
#from app.api import auth

# cria a aplicação FastAPI com título e versão
app = FastAPI(title="autht-api-fast", version="1.0.0")

# registra o roteador de autenticação em /auth
#app.include_router(auth.router, prefix="/auth", tags=["auth"])

# registra o roteador de usuários em /users
# OBS: o objeto `user` precisa estar importado para que esta linha funcione
#app.include_router(user.router, prefix="/users", tags=["users"])

# rota de saúde para verificar se a aplicação está rodando
@app.get("/health",tags=["infra"])
def health():
    return {"status": "ok"}

