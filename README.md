## Arquitetura

O projeto utiliza uma arquitetura em camadas, separando responsabilidades entre rotas HTTP, regras de negócio, modelos de banco, schemas de validação e infraestrutura base.

- `api/`: camada de entrada HTTP, responsável pelas rotas FastAPI.
- `services/`: camada de regras de negócio da aplicação.
- `models/`: modelos ORM SQLAlchemy que representam as tabelas do banco.
- `schemas/`: contratos Pydantic de entrada e saída da API.
- `core/`: configurações, conexão com banco e segurança.

Essa separação facilita manutenção, testes, evolução do código e evita concentração de lógica nas rotas.
