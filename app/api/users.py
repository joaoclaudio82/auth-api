
#Aqui definimos as rotas relacionadas a usuários, incluindo a rota protegida /users/me que retorna os dados do usuário autenticado.
#A função get_current_user é uma dependência que valida o token JWT e retorna o usuário correspondente. 
#Se o token for inválido ou o usuário não existir, ela lança uma HTTPException 401 Unauthorized.   

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User
from app.schemas.user import UserRead
from app.services import user_service


# ===== CONFIGURAÇÃO DO ROTEADOR =====
# Cria um roteador FastAPI para rotas relacionadas a usuários.
# Todas as rotas definidas aqui terão prefixo /users.
router = APIRouter(prefix="/users", tags=["users"])


# ===== CONFIGURAÇÃO DO SCHEME OAUTH2 =====
# OAuth2PasswordBearer define o esquema de autenticação via token bearer.
# tokenUrl indica onde o cliente deve enviar as credenciais para obter o token.
# No caso, o login é feito em POST /auth/login.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    # ARGUMENTO 1: token JWT enviado no header Authorization: Bearer <token>
    # Depends(oauth2_scheme) manda o FastAPI extrair o token automaticamente.
    db: Session = Depends(get_db),
    # ARGUMENTO 2: sessão do banco de dados para buscar o usuário.
    # get_db é uma dependência que abre/fecha a sessão corretamente.
) -> User:
    """
    Valida o token JWT e retorna o usuário autenticado.

    Saídas:
    - Retorna o objeto User quando o token é válido e o usuário existe.
    - Lança HTTPException 401 quando o token é inválido/expirado ou o usuário não existe.
    """

    # decode_token transforma o JWT em email do usuário.
    # Se o token for inválido ou expirado, ele retorna None.
    email = decode_token(token)

    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
        )

    # Busca o usuário no banco pelo email obtido do token.
    user = user_service.get_by_email(db, email)

    if user is None:
        # Se o token era válido, mas o usuário não existe mais, o acesso também é negado.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado",
        )

    return user


@router.get("/me", response_model=UserRead)
# Endpoint protegido que retorna os dados do usuário atualmente autenticado.
# response_model=UserRead garante que apenas os campos públicos do usuário são retornados.
def read_me(current_user: User = Depends(get_current_user)):
    """
    Lê os dados do usuário autenticado.

    O parâmetro current_user é preenchido pela dependência get_current_user.
    Se o token no header for inválido, o FastAPI retorna 401 antes de entrar na função.
    """
    return current_user