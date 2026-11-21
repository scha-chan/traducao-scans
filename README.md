# Manga Translator

Aplicação de tradução de mangás com OCR, pipeline de IA e editor de traduções.

## Stack

| Camada    | Tecnologia                              |
|-----------|-----------------------------------------|
| Frontend  | Angular 22 (standalone, signals)        |
| Backend   | FastAPI + SQLAlchemy async + Alembic    |
| Worker    | ARQ (Redis queue) + MarianMT / Claude   |
| Banco     | PostgreSQL 16                           |
| Cache     | Redis 7                                 |

---

## Deploy com Docker Compose

### 1. Variáveis de ambiente

Crie um `.env` na raiz do projeto:

```env
POSTGRES_PASSWORD=senha_segura
ANTHROPIC_API_KEY=sk-ant-...   # opcional, apenas se usar Claude
```

Variáveis opcionais com seus defaults:

```env
POSTGRES_DB=manga_translator
POSTGRES_USER=manga
BACKEND_PORT=8000
FRONTEND_PORT=4200
API_BASE_URL=http://localhost:8000
```

### 2. Subir os serviços

```bash
docker compose up -d
```

### 3. Aplicar as migrations do banco

**Obrigatório na primeira execução e após cada atualização que adicione migrations.**

```bash
docker compose exec backend alembic upgrade head
```

Para verificar a versão atual:

```bash
docker compose exec backend alembic current
```

### 4. Acessar

- Frontend: <http://localhost:4200>
- API: <http://localhost:8000>
- Swagger: <http://localhost:8000/docs>

---

## Desenvolvimento com Docker (hot-reload)

O arquivo `docker-compose.override.yml` já está no repositório. Quando presente, o Docker Compose o usa automaticamente — sem nenhuma flag extra.

Ele monta `./backend` como volume dentro do container e liga o `--reload` do uvicorn, então qualquer alteração em arquivos `.py` reinicia o servidor em segundos, sem rebuild.

```bash
# Primeira vez (ou após trocar a imagem base):
docker compose up -d --build

# A partir daí, mudanças no código Python refletem automaticamente.
# Para reiniciar o worker manualmente após mudanças:
docker compose restart worker
```

> **Frontend:** o container do frontend é uma imagem Nginx estática (precisa rebuild após mudanças). Para desenvolvimento do frontend, prefira rodar `ng serve` localmente apontando para o backend Docker (`API_BASE_URL=http://localhost:8000`).

---

## Desenvolvimento local (sem Docker)

### Backend

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

### Worker

```bash
cd backend
arq worker.main.WorkerSettings
```

### Frontend

```bash
cd frontend
npm install
ng serve
```

---

## Migrations

As migrations ficam em `backend/alembic/versions/`. Cada atualização do projeto pode incluir novas migrations; sempre rode `alembic upgrade head` após um `git pull`.

| Número | Descrição                            |
|--------|--------------------------------------|
| 0001   | Schema inicial                       |
| 0007   | Tabela page_slices                   |
| 0008   | Colunas source_lang / target_lang    |

---

## Variáveis de ambiente do worker (modelos ML)

| Variável                   | Default (Docker)                            |
|----------------------------|---------------------------------------------|
| `MANGA_OCR_MODEL`          | `/app/backend/models/manga-ocr`             |
| `TRANSLATION_JA_EN_MODEL`  | `/app/backend/models/opus-mt-ja-en`         |
| `TRANSLATION_EN_PT_MODEL`  | `/app/backend/models/opus-mt-tc-big-en-pt`  |
| `LLM_PROVIDER`             | `claude` (ou `ollama` se `OLLAMA_BASE_URL`) |
| `ANTHROPIC_API_KEY`        | —                                           |
| `OLLAMA_BASE_URL`          | `http://localhost:11434`                    |
