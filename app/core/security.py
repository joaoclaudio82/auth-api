
# ============================================================================
# IMPORTAÇÕES - Bibliotecas necessárias para autenticação e segurança
# ============================================================================

from datetime import datetime, timedelta, timezone
# datetime: classe para trabalhar com datas e horas
# timedelta: classe para calcular diferenças de tempo (exemplo: adicionar 30 minutos)
# timezone: classe para trabalhar com fusos horários
# PORQUÊ: Precisamos delas para calcular quando um token JWT vai expirar

from jose import JWTError, jwt
# jose: biblioteca para criar e decodificar tokens JWT (JSON Web Tokens)
# JWTError: exceção que é lançada quando há erro na decodificação do token
# jwt: funções para criar (encode) e decodificar (decode) tokens
# PORQUÊ: JWT é um padrão seguro para autenticação em APIs REST

from passlib.context import CryptContext
# passlib: biblioteca para hash seguro de senhas
# CryptContext: classe que gerencia diferentes algoritmos de criptografia
# PORQUÊ: Nunca devemos guardar senhas em texto plano no banco de dados

from app.core.config import settings
# settings: objeto que contém todas as configurações do projeto
# Inclui: database_url, secret_key, algorithm, access_token_expire_minutes
# PORQUÊ: Centraliza configurações sensíveis e facilita manutenção


# ============================================================================
# CONFIGURAÇÃO DE HASH DE SENHAS
# ============================================================================

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# CryptContext: cria um contexto de criptografia
# schemes=["bcrypt"]: usa o algoritmo bcrypt (considerado muito seguro)
# deprecated="auto": se um hash antigo usar outro algoritmo, atualiza automaticamente
# PORQUÊ: bcrypt é uma das formas mais seguras de guardar senhas,
#         pois é lento e difícil de fazer brute force (testar todas as senhas possíveis)


# ============================================================================
# FUNÇÕES DE SEGURANÇA
# ============================================================================

def get_password_hash(password: str) -> str:
    """
    Cria um hash seguro de uma senha em texto plano.

    Args:
        password (str): Senha em texto plano que o usuário digitou

    Returns:
        str: Hash criptografado da senha (nunca retorna a senha original)

    PORQUÊ: Quando um usuário se registra, nós guardamos o hash (não a senha).
            Se alguém invadir o banco de dados, não terá as senhas originais.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica se uma senha em texto plano corresponde a um hash armazenado.

    Args:
        plain_password (str): Senha em texto plano (digitada pelo usuário no login)
        hashed_password (str): Hash armazenado no banco de dados

    Returns:
        bool: True se a senha está correta, False caso contrário

    PORQUÊ: No login, o usuário digita a senha. Precisamos comparar
            o hash dessa senha com o hash guardado no banco.
            Não podemos comparar textos diretamente porque não guardamos o texto original.
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str) -> str:
    """
    Cria um token JWT para autenticação do usuário.

    Args:
        subject (str): Identificador do usuário (geralmente o ID ou email)

    Returns:
        str: Token JWT criptografado que o cliente vai usar nas requisições

    PORQUÊ: Após fazer login, o usuário recebe um token.
            Ele envia esse token em cada requisição para provar que é ele.
            O servidor valida o token sem precisar consultar o banco cada vez.
    """

    # Calcula quando o token vai expirar
    # datetime.now(timezone.utc): pega o horário atual em UTC (padrão internacional)
    # timedelta(minutes=...): adiciona X minutos ao horário atual
    # Exemplo: Se é 10:00 e access_token_expire_minutes=30, expira às 10:30
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )

    # Conteúdo do token (o que vai estar criptografado dentro do JWT)
    payload = {
        "sub": subject,  # "sub" = subject (convenção JWT para identificador do usuário)
        "exp": expire,   # "exp" = expiration (convenção JWT para data de expiração)
    }

    # Criptografa o payload usando a chave secreta do projeto
    # Só quem tem a secret_key consegue decodificar e validar o token
    return jwt.encode(
        payload,
        settings.secret_key,  # Chave secreta do projeto (tipo uma senha da API)
        algorithm=settings.algorithm,  # Algoritmo usado (HS256 é padrão seguro)
    )


def decode_token(token: str) -> str | None:
    """
    Decodifica um token JWT e extrai o identificador do usuário.

    Args:
        token (str): Token JWT recebido do cliente

    Returns:
        str | None: O identificador do usuário (subject) se o token for válido,
                   None se o token for inválido ou expirado

    PORQUÊ: Quando o cliente faz uma requisição com um token,
            nós decodificamos para saber quem é o usuário.
            Se o token for inválido ou expirado, rejeitamos a requisição.
    """
    try:
        # Tenta decodificar o token
        # O jwt.decode valida automaticamente:
        # 1. Se a assinatura está correta (usando a secret_key)
        # 2. Se o token não expirou (comparando com a data atual)
        payload = jwt.decode(
            token,
            settings.secret_key,  # Precisa da mesma chave para validar
            algorithms=[settings.algorithm],  # Especifica quais algoritmos são aceitos
        )

        # Se conseguiu decodificar, extrai o "subject" (ID do usuário)
        # .get("sub") retorna o valor ou None se a chave não existir
        return payload.get("sub")

    except JWTError:
        # Se houver qualquer erro (token inválido, expirado, assinatura errada, etc)
        # retorna None, indicando que o token não é válido
        return None