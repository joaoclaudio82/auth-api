# ============================================================================
# USER SERVICE - Camada de Negócio para Gerenciamento de Usuários
# ============================================================================
# 
# Este arquivo contém a LÓGICA DE NEGÓCIO relacionada a usuários.
# É uma camada intermediária entre o banco de dados (models) e os endpoints (routes).
# Aqui fica a "inteligência" do application: validações, processamento, regras.
#
# PORQUÊ separar em serviço? Para deixar o código organizado e reutilizável.
# Se precisar criar um usuário em 3 endpoints diferentes, chamamos a mesma função.


# ============================================================================
# IMPORTAÇÕES
# ============================================================================

from sqlalchemy.orm import Session
# Session: Representa uma conexão lógica com o banco de dados
# É como uma "conversa" com o banco de dados que fica aberta durante o tempo que precisamos
# Através dela, executamos queries, salvamos dados, e gerenciamos transações
# PORQUÊ: Sem Session, não conseguimos interagir com o banco de dados


from app.core.security import get_password_hash, verify_password
# get_password_hash: Função que transforma uma senha em texto plano em um hash seguro
# verify_password: Função que compara uma senha digitada com um hash armazenado no banco
# PORQUÊ: Precisamos delas para registrar novos usuários e fazer autenticação


from app.models.user import User
# User: Modelo SQLAlchemy que representa a tabela "users" no banco de dados
# Define colunas como: id, email, hashed_password, created_at, etc.
# É a ponte entre Python (OOP) e o banco de dados (SQL)
# PORQUÊ: Precisamos saber qual é a estrutura de dados do usuário


from app.schemas import user
# Schemas: Definem a estrutura dos dados que entram/saem da API
# São como "contratos" que garantem que os dados têm o formato correto
# PORQUÊ: Validação automática dos dados recebidos do cliente


from app.schemas.user import UserCreate
# UserCreate: Schema que define quais dados são necessários para criar um usuário
# Exemplo: { "email": "user@example.com", "password": "senha123" }
# PORQUÊ: Especificar exatamente quais campos o cliente deve enviar


# ============================================================================
# FUNÇÃO 1: Buscar usuário pelo email
# ============================================================================

def get_by_email(db: Session, email: str) -> User | None:
    """
    Busca um usuário no banco de dados pelo seu email.

    Args:
        db (Session): Conexão com o banco de dados
        email (str): Email do usuário a buscar

    Returns:
        User | None: O objeto User encontrado, ou None se não existir

    PORQUÊ: Emails são únicos, então é comum buscar usuários por email.
            Também é usado para verificar se um email já está registrado.
    """
    # db.query(User): Inicia uma query SELECT na tabela User
    # .filter(User.email == email): Filtra pelo email específico (WHERE email = 'x')
    # .first(): Retorna o primeiro resultado, ou None se não houver nenhum
    return db.query(User).filter(User.email == email).first()


# ============================================================================
# FUNÇÃO 2: Criar novo usuário (REGISTRAR)
# ============================================================================

def create_user(db: Session, data: UserCreate) -> User:
    """
    Cria um novo usuário no banco de dados.

    Args:
        db (Session): Conexão com o banco de dados
        data (UserCreate): Dados do novo usuário (email, password)

    Returns:
        User: O objeto User recém-criado (com ID gerado pelo banco)

    PORQUÊ: Quando um novo usuário se registra, precisamos salvá-lo no banco.
            Essa função encapsula toda a lógica: criptografar senha, salvar, etc.

    FLUXO:
        1. Recebe email e senha em texto plano
        2. Criptografa a senha usando bcrypt
        3. Cria um objeto User com email + senha criptografada
        4. Salva no banco de dados
        5. Retorna o usuário criado (com ID gerado)
    """

    # Cria um novo objeto User em memória (ainda não está no banco)
    # email: armazena diretamente o email
    # hashed_password: armazena a senha criptografada (não a senha original!)
    # get_password_hash(data.password): transforma "senha123" em "$2b$12$abc..."
    user = User(
        email=data.email,
        hashed_password=get_password_hash(data.password),
    )

    # db.add(user): Adiciona o usuário à "sessão" (mas ainda não salvou no banco)
    # É como adicionar um item à cesta de compras - ainda não confirmou
    db.add(user)

    # db.commit(): CONFIRMA e salva o usuário no banco de dados
    # É como clicar em "Finalizar compra"
    # Neste ponto: INSERT INTO users (email, hashed_password) VALUES (...)
    db.commit()

    # db.refresh(user): Recarrega os dados do usuário do banco
    # PORQUÊ: O banco gerou um ID automático que precisamos saber
    # Agora user.id tem o ID gerado pelo banco
    db.refresh(user)

    # Retorna o usuário completo (com ID, email, etc.)
    return user


# ============================================================================
# FUNÇÃO 3: Autenticar usuário (LOGIN)
# ============================================================================

def authenticate(db: Session, email: str, password: str) -> User | None:
    """
    Valida as credenciais de um usuário (email + senha).

    Args:
        db (Session): Conexão com o banco de dados
        email (str): Email digitado pelo usuário
        password (str): Senha digitada pelo usuário (em texto plano)

    Returns:
        User | None: O objeto User se as credenciais forem corretas,
                    None se o email não existir ou a senha estiver errada

    PORQUÊ: No login, precisamos verificar se o email existe
            e se a senha está correta (comparando hashes).

    FLUXO:
        1. Busca o usuário pelo email
        2. Se não existir → retorna None (login falhou)
        3. Se existir → compara a senha digitada com o hash armazenado
        4. Se a senha estiver errada → retorna None
        5. Se tudo correto → retorna o usuário
    """

    # Tenta buscar o usuário no banco usando o email
    # Resultado: Um objeto User, ou None se não existir
    user = get_by_email(db, email)

    # VERIFICAÇÃO 1: Email existe no banco?
    if not user:
        # Email não foi encontrado no banco de dados
        # Retorna None (indicando falha na autenticação)
        return None

    # VERIFICAÇÃO 2: Senha está correta?
    # verify_password(senha_digitada, hash_armazenado):
    # - Faz hash da senha digitada
    # - Compara com o hash armazenado no banco
    # - Retorna True se forem iguais, False caso contrário
    if not verify_password(password, user.hashed_password):
        # Senha digitada não corresponde ao hash armazenado
        # Retorna None (indicando falha na autenticação)
        return None

    # Se chegou aqui, email existe E senha está correta ✅
    # Retorna o usuário (será usado para gerar um JWT token)
    return user


''' 25. Por que retornar None em vez de lançar HTTPException?

No serviço, evitamos fazer isso:

raise HTTPException(status_code=401, detail="Credenciais inválidas")

Isso porque HTTPException pertence à camada de API.
O serviço não deveria conhecer detalhes de HTTP.
O serviço deve apenas dizer:

autenticou

ou

não autenticou

A rota decide qual resposta HTTP será enviada ao cliente.
Isso é uma boa prática de arquitetura. '''