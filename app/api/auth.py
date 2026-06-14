# ===== IMPORTAÇÕES =====
from fastapi import APIRouter, Depends, HTTPException, status
# APIRouter: Cria um roteador FastAPI para agrupar rotas relacionadas
# Depends: Sistema de injeção de dependências do FastAPI
# HTTPException: Classe para retornar erros HTTP com status_code e detail (mensagem)
# status: Módulo com constantes de status HTTP (200, 401, 409, etc)

from fastapi.security import OAuth2PasswordRequestForm
# OAuth2PasswordRequestForm: Schema pré-definido do FastAPI que aceita username e password
# Usamos para padronizar o formato de login (automaticamente cria um formulário form-urlencoded)

from sqlalchemy.orm import Session
# Session: Objeto que gerencia a conexão com o banco de dados
# Permite fazer queries e commits de forma segura

from app.core.database import get_db
# get_db: Função que retorna uma nova sessão de banco de dados para cada requisição
# Usamos com Depends() para que o FastAPI injete automaticamente a sessão

from app.core.security import create_access_token
# create_access_token: Função que gera um JWT (token de autenticação)
# O token é usado para autenticar requisições futuras do usuário

from app.schemas.user import Token, UserCreate, UserRead
# Token: Schema que define a resposta de login (contém access_token e token_type)
# UserCreate: Schema com os dados necessários para criar um novo usuário (email, password, etc)
# UserRead: Schema que define quais campos do usuário são retornados (sem password!)

from app.services import user_service
# user_service: Módulo com funções de negócio para usuários
# Contém: create_user, authenticate, get_by_email, etc


# ===== CONFIGURAÇÃO DO ROTEADOR =====
# Cria um roteador FastAPI que agrupa todas as rotas de autenticação
# prefix="/auth": Todas as rotas serão prefixadas com /auth (ex: POST /auth/register)
# tags=["auth"]: Agrupa as rotas sob a tag "auth" na documentação Swagger
router = APIRouter(prefix="/auth", tags=["auth"])


# ===== ROTA DE REGISTRO (SIGN UP) =====
# Este endpoint permite que novos usuários se cadastrem no sistema
@router.post("/register", response_model=UserRead, status_code=201)
# @router.post(): Registra uma rota HTTP POST no roteador
# Quando alguém faz: POST /auth/register
# "/register": Caminho da rota (completo fica: /auth/register)
# response_model=UserRead: Define que a resposta será serializada como UserRead
#   Isso significa: só retorna os campos definidos em UserRead (sem password!)
# status_code=201: Retorna HTTP 201 (Created) em vez de 200 (sucesso com novo recurso criado)

def register(
    data: UserCreate,  # ARGUMENTO 1: Dados do novo usuário (email, password)
                       # UserCreate é um schema Pydantic que valida os dados
                       # FastAPI automaticamente extrai do body da requisição e valida
    
    db: Session = Depends(get_db)  # ARGUMENTO 2: Sessão do banco de dados
                                    # Depends(get_db) injeta automaticamente uma nova sessão
                                    # Cada requisição recebe uma sessão isolada e segura
):
    """
    Registra um novo usuário no sistema.
    
    FLUXO:
    1. Verifica se o e-mail já existe (evita duplicatas)
    2. Se existe: retorna erro 409 Conflict
    3. Se não existe: cria o usuário com senha criptografada
    4. Retorna os dados do usuário criado (sem password)
    """
    
    # Verifica se já existe um usuário com esse e-mail
    if user_service.get_by_email(db, data.email):
        # Se encontrou, retorna erro HTTP 409 (Conflict - recurso já existe)
        raise HTTPException(
            status_code=409,
            detail="E-mail já cadastrado",  # Mensagem que o cliente recebe
        )

    # Se não existe, cria o novo usuário no banco de dados
    # user_service.create_user:
    #   - Recebe: sessão do BD e dados UserCreate (email + password)
    #   - Faz: criptografa a password, cria registro no BD, commit
    #   - Retorna: objeto User com id gerado pelo banco
    return user_service.create_user(db, data)


# ===== ROTA DE LOGIN (AUTENTICAÇÃO) =====
# Este endpoint autentica o usuário e retorna um token JWT
@router.post("/login", response_model=Token)
# Quando alguém faz: POST /auth/login
# response_model=Token: Retorna um objeto Token (access_token + token_type)

def login(
    form: OAuth2PasswordRequestForm = Depends(),
    # ARGUMENTO 1: Formulário com credenciais de login
    # OAuth2PasswordRequestForm espera:
    #   - username: email do usuário (nesse caso)
    #   - password: senha em texto plano (será validada contra hash)
    # Depends() injeta automaticamente do corpo da requisição (form-urlencoded)
    # O FastAPI automaticamente parseia form fields para esse objeto
    
    db: Session = Depends(get_db),
    # ARGUMENTO 2: Sessão do banco de dados (para buscar o usuário)
):
    """
    Autentica um usuário e retorna um token de acesso JWT.
    
    FLUXO:
    1. Busca o usuário no banco por email
    2. Valida se a senha está correta
    3. Se falhar: retorna erro 401 Unauthorized
    4. Se passar: gera um JWT e retorna ao cliente
    5. Cliente usa esse JWT em requisições futuras no header: Authorization: Bearer <token>
    """
    
    # Autentica o usuário (busca no BD e verifica password)
    # user_service.authenticate:
    #   - Recebe: sessão do BD, email e password em texto plano
    #   - Faz: busca usuário por email, compara password hash com password fornecido
    #   - Retorna: objeto User se válido, None se inválido
    user = user_service.authenticate(
        db=db,
        email=form.username,  # form.username é o email (por padrão OAuth2 chama assim)
        password=form.password,  # password em texto plano (será criptografado para comparação)
    )

    # Se authenticate retornar None, significa credenciais inválidas
    if not user:
        # Retorna erro HTTP 401 (Unauthorized - não autenticado)
        # Não dizemos se é email errado ou password errado (segurança: não revela dados)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,  # 401 = não autenticado
            detail="Credenciais inválidas",  # Mensagem genérica
        )

    # Se as credenciais são válidas, gera um JWT
    # create_access_token:
    #   - Recebe: subject (identificador único = email do usuário)
    #   - Faz: cria um JWT com claims (informações codificadas)
    #          assina com secret_key, adiciona expiração (TTL)
    #   - Retorna: string JWT (exemplo: eyJhbGciOiJIUzI1NiIs...)
    access_token = create_access_token(subject=user.email)

    # Retorna o token ao cliente
    # Token é um schema que contém:
    #   - access_token: o JWT gerado acima
    #   - token_type: "bearer" (sempre "bearer" para JWT em OAuth2)
    # Cliente usa: Authorization: Bearer <access_token>
    return Token(access_token=access_token)


#No FastAPI, uso OAuth2PasswordBearer como dependência para extrair o token Bearer do header Authorization. 
# Ele não valida o JWT por si só; apenas captura o token e o entrega como string. 
# A validação real é feita na função decode_token, que verifica assinatura e expiração. 
# Depois, uso o sub do token para buscar o usuário no banco e liberar o acesso à rota protegida.