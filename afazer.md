# Roadmap: de júnior avançado → app com cara de pleno

Documento passo a passo, em ordem de prioridade. Cada fase entrega algo visível e melhora a impressão técnica do projeto.

---

## Como usar este guia

- **Fase 1–2:** higiene e qualidade — impacto imediato em code review
- **Fase 3–4:** segurança e consistência — o que pleno sabe citar em entrevista
- **Fase 5–6:** operação e escopo — diferencial forte no portfólio
- **Fase 7:** apresentação — como vender o projeto

Estimativa total: **2–4 semanas** trabalhando aos poucos.

---

## Fase 1 — Higiene do repositório (1–2 dias)

**Objetivo:** projeto organizado, sem “cheiro de estudante”.

### Passo 1.1 — Limpar arquivos soltos

- [ x] Apagar o arquivo com nome estranho na raiz (`DATABASE_URL=postgresql+...`)
- [ x] Apagar `Untitled` ou mover conteúdo para `.env` se ainda for útil
- [x ] Garantir que `.env` está no `.gitignore` e **nunca** vai pro Git
- [ x] Manter só `.env.example` versionado

### Passo 1.2 — README principal enxuto

- [x] Criar um `README.md` curto (máx. ~80 linhas) com:
  - o que é o projeto
  - stack
  - como rodar (Docker + manual)
  - endpoints principais
  - como rodar testes
- [x] Mover detalhes longos para `docs/` e `ARQUITETURA.md` (já existem)

### Passo 1.3 — Estrutura de docs clara

```text
README.md                        → entrada rápida
docs/README.md                   → índice da documentação
docs/onboarding.md               → passo a passo
docs/guia-completo.md            → consolidado
docs/relatorio-implementacao.md  → relatório histórico (ex-readme-old)
ARQUITETURA.md                   → aprofundamento
```

**Entrega:** quem abre o repo entende em 2 minutos.

---

## Fase 2 — Qualidade de código profissional (2–3 dias)

**Objetivo:** código que parece escrito para time, não para apostila.

### Passo 2.1 — Reduzir comentários didáticos

Prioridade: `app/api/auth.py`, `app/services/user_service.py`, `app/core/security.py`

**Antes (pleno não escreve assim):**

```python
# Depends: Sistema de injeção de dependências do FastAPI
# HTTPException: Classe para retornar erros HTTP...
```

**Depois:**

- Remover comentários que repetem o óbvio
- Manter só onde há regra de negócio não trivial (ex.: por que `authenticate` retorna `None`)

**Meta:** `auth.py` com ~40 linhas, não 160.

### Passo 2.2 — Corrigir code smells

- [ ] Remover imports não usados em `database.py` (`os`, `declarative_base`)
- [ ] Remover `from app.schemas import user` não usado em `user_service.py`
- [ ] Remover código morto após `raise ValueError` em `create_user`
- [ ] Padronizar idioma dos comentários (português **ou** inglês — escolha um)

### Passo 2.3 — Toolchain moderna

Criar `pyproject.toml` com:

```toml
[tool.ruff]
line-length = 88
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP"]

[tool.mypy]
python_version = "3.12"
strict = true
```

- [ ] Instalar `ruff` e `mypy`
- [ ] Rodar localmente até zerar erros relevantes
- [ ] Adicionar ao CI (Fase 6)

**Entrega:** diff limpo, reviewer não se perde em comentários.

---

## Fase 3 — Consistência de regras de negócio (1–2 dias)

**Objetivo:** comportamento coerente em todo o fluxo.

### Passo 3.1 — Usuário inativo

Hoje:

- Login funciona para inativo
- `/users/me` retorna 403

**Pleno faz consistente.** Escolha uma regra e aplique em todo lugar:

| Opção | Comportamento |
|-------|---------------|
| A (recomendada) | `authenticate()` retorna `None` se `not user.is_active`; login → 401 |
| B | Login ok, mas rotas protegidas → 403 |

- [ ] Implementar a opção escolhida
- [ ] Atualizar testes (`test_users_me_usuario_inativo` e criar `test_login_usuario_inativo` se opção A)
- [ ] Documentar a decisão em 2 linhas no `docs/`

### Passo 3.2 — JWT: `sub` com ID, não e-mail

- [ ] Mudar `create_access_token(subject=str(user.id))`
- [ ] Em `get_current_user`, buscar por `id` (criar `get_by_id` no service)
- [ ] Adicionar teste: token válido encontra usuário pelo id

**Por quê:** e-mail pode mudar; id é estável. Pleno pensa nisso.

### Passo 3.3 — Tratamento de erros HTTP padronizado

- [ ] Criar handler global ou usar `detail` consistente
- [ ] Garantir que 401 no login sempre diz “Credenciais inválidas” (não vazar se e-mail existe)

**Entrega:** regras previsíveis, testes alinhados.

---

## Fase 4 — Segurança além do básico (3–5 dias)

**Objetivo:** mostrar que você pensa em produção, não só em “funciona local”.

### Passo 4.1 — Rate limiting no login

- [ ] Adicionar `slowapi` ou middleware simples
- [ ] Limitar `POST /auth/login` (ex.: 5 tentativas/minuto por IP)
- [ ] Teste: após N tentativas → 429

### Passo 4.2 — Headers de segurança (opcional mas valorizado)

- [ ] Middleware com headers básicos ou usar lib adequada
- [ ] CORS configurável via `.env` se houver front-end

### Passo 4.3 — Política de senha um pouco mais forte

- [ ] Manter 8–72 chars
- [ ] (Opcional) exigir letra + número via validador Pydantic customizado
- [ ] Teste para senha fraca rejeitada

### Passo 4.4 — Refresh token (grande diferencial)

Fluxo mínimo:

```text
POST /auth/login     → access_token + refresh_token
POST /auth/refresh   → novo access_token
POST /auth/logout    → invalida refresh (tabela refresh_tokens)
```

- [ ] Migration: tabela `refresh_tokens` (user_id, token_hash, expires_at, revoked)
- [ ] Guardar hash do refresh, nunca o token puro
- [ ] 3 endpoints + 4–5 testes

**Entrega:** módulo auth “completo o suficiente” para portfólio pleno.

---

## Fase 5 — Testes de verdade (2–3 dias)

**Objetivo:** confiança além do SQLite em memória.

### Passo 5.1 — Expandir testes unitários/integração HTTP

Adicionar cenários que faltam:

- [ ] Token expirado (mock de `exp` ou `ACCESS_TOKEN_EXPIRE_MINUTES=0` no teste)
- [ ] `IntegrityError` no register (simular corrida, se possível)
- [ ] `GET /health` retorna 200
- [ ] Refresh token (se implementado)

### Passo 5.2 — Testes com PostgreSQL (opcional, muito valorizado)

- [ ] Job no CI com service `postgres:16`
- [ ] 1–2 testes de integração contra Postgres real (register + login)
- [ ] Ou usar `testcontainers-python`

### Passo 5.3 — Cobertura mínima

- [ ] `pytest --cov=app --cov-report=term-missing`
- [ ] Meta: **≥ 85%** em `services/`, `api/`, `core/security.py`
- [ ] Badge de coverage no README (opcional)

**Entrega:** “testes automatizados” deixa de ser só marketing.

---

## Fase 6 — DevOps e operação (2–3 dias)

**Objetivo:** app deployável e observável.

### Passo 6.1 — CI completo

Atualizar `.github/workflows/ci.yml`:

```yaml
- ruff check .
- mypy app
- pytest -v --cov=app
```

- [ ] CI falha se lint, types ou testes quebrarem

### Passo 6.2 — Logging estruturado

- [ ] Configurar `logging` no startup (`main.py`)
- [ ] Logar: register (sem senha), login falho/sucesso, erros 500
- [ ] Formato JSON ou padrão legível com timestamp

### Passo 6.3 — Healthcheck real

Evoluir `GET /health`:

```json
{
  "status": "ok",
  "database": "connected"
}
```

- [ ] Fazer query simples no banco (`SELECT 1`)
- [ ] Se banco down → 503

### Passo 6.4 — Docker production-ready

- [ ] Multi-stage no `Dockerfile` (opcional)
- [ ] Usuário non-root no container
- [ ] `.dockerignore` revisado
- [ ] Documentar diferença dev vs prod no `docs/docker-compose.md`

**Entrega:** projeto “sobe em qualquer máquina” com confiança.

---

## Fase 7 — Escopo que impressiona (1 semana, escolha 1–2)

**Objetivo:** ir além do CRUD mínimo sem virar monstro.

Escolha **uma** feature extra:

| Feature | Esforço | Impacto em entrevista |
|---------|---------|------------------------|
| **Reset de senha** (token por e-mail mock) | Médio | Alto |
| **Roles** (user/admin + guard) | Médio | Alto |
| **Paginação** `GET /users` (só admin) | Baixo | Médio |
| **OpenAPI tags + exemplos** no Swagger | Baixo | Médio |

Exemplo mínimo de roles:

- [ ] Coluna `role` no User (`user` | `admin`)
- [ ] `get_current_admin` dependency
- [ ] `GET /users` listando usuários (admin only)

**Entrega:** não é só “login e cadastro” — há domínio real.

---

## Fase 8 — Apresentação para entrevista (1 dia)

**Objetivo:** contar a história certa do projeto.

### Passo 8.1 — Seção “Decisões técnicas” no README

Documentar em bullet points:

- Por que arquitetura em camadas
- Por que JWT stateless
- Por que bcrypt
- Trade-offs (sem refresh token inicialmente → depois adicionou)
- O que **não** foi feito e por quê (escopo)

### Passo 8.2 — Diagrama simples

Manter o diagrama de camadas do `ARQUITETURA.md` no README ou link direto.

### Passo 8.3 — Roteiro de demo (5 min)

1. `docker compose up`
2. Swagger → register → login → Authorize → `/users/me`
3. `pytest -v`
4. Mostrar teste de usuário inativo ou rate limit
5. Abrir `user_service.py` e explicar separação HTTP vs negócio

### Passo 8.4 — Frases prontas para entrevista

- “Separei regra de negócio da camada HTTP para facilitar testes e reuso.”
- “UserRead nunca expõe hash; validação no Pydantic evita senha > 72 chars por limitação do bcrypt.”
- “Tratei corrida de e-mail duplicado com IntegrityError + rollback.”
- “Para produção, evoluiria com refresh token, rate limit e observabilidade.”

---

## Checklist resumida (ordem de execução)

```text
Semana 1
  □ Limpar repo + README enxuto
  □ Reduzir comentários + ruff/mypy
  □ Consistência is_active + sub=id no JWT

Semana 2
  □ Rate limit no login
  □ Refresh token (ou reset de senha)
  □ Testes faltantes + coverage

Semana 3
  □ CI com lint + types + cov
  □ Logging + health com DB
  □ 1 feature extra (roles ou admin)

Semana 4 (opcional)
  □ Testes com Postgres no CI
  □ Polir docs + roteiro de demo
```

---

## Critérios: “agora tem cara de pleno”

Marque quando puder dizer **sim** a tudo:

- [ ] Código limpo, sem comentário de tutorial em excesso
- [ ] CI roda lint + testes (e mypy se possível)
- [ ] ≥ 10 testes cobrindo happy path e erros
- [ ] Regras de negócio consistentes (inativo, JWT, erros)
- [ ] Pelo menos **1** hardening de segurança (rate limit ou refresh token)
- [ ] Docker sobe com um comando
- [ ] README explica decisões, não só “como rodar”
- [ ] Você explica trade-offs em 5 minutos sem ler slides

---

## O que **não** fazer (armadilhas)

- Não adicionar microserviços, Kubernetes ou GraphQL só para impressionar
- Não trocar stack (ex.: migrar tudo para async) sem motivo
- Não documentar demais no código — docs vão para `docs/`
- Não commitar `.env`, secrets ou arquivos acidentais na raiz

---

## Prioridade se tiver pouco tempo (top 5)

1. Limpar código e comentários
2. Ruff + pytest no CI
3. Consistência `is_active` + JWT com `user.id`
4. Rate limit no login
5. Refresh token **ou** roles/admin

Com só esses 5, o projeto já sobe um degrau claro na percepção de pleno.
