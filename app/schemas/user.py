#aqui temos os modelos Pydantic para criação e leitura de usuários, bem como para tokens de autenticação. 
# Esses modelos são usados para validar e serializar os dados de entrada e saída da API, garantindo que os dados estejam no formato correto e atendam às 
# restrições definidas. O modelo UserCreate é usado para criar novos usuários, o UserRead é usado para ler informações dos usuários existentes, e o Token é usado para representar o 
# token de acesso gerado durante a autenticação.


# Define os modelos Pydantic para criação e leitura de usuários, bem como para tokens de autenticação.    
from pydantic import BaseModel, EmailStr, ConfigDict

# Define o modelo UserCreate para criação de usuários, com campos de email e senha.
class UserCreate(BaseModel):
    email: EmailStr
    password: str

# Define o modelo UserRead para leitura de usuários, com campos de id, email e status de atividade. O ConfigDict é usado para permitir a criação do modelo a partir de atributos de classe.
class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)# Permite criar o modelo a partir de atributos de classe, facilitando a conversão de objetos ORM para modelos Pydantic.

    id: int
    email: EmailStr
    is_active: bool

# Define o modelo Token para representar o token de acesso e seu tipo, com campos de access_token e token_type.
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"