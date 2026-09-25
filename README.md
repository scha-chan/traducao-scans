# Manga Translator Agent

Ferramenta para tradução de mangás japoneses via IA: detecta regiões de texto, faz OCR, classifica e traduz os balões.

## Estrutura do repositório

```
traducao-scans/
├── frontend/      # Angular — interface de revisão e download
├── backend/       # FastAPI — API REST e orquestrador do pipeline
├── contracts/     # Schemas JSON e contratos compartilhados entre frontend e backend
├── prompts/       # Prompts de IA versionados (OCR, tradução, classificação)
└── docs/          # PRD, especificação do frontend e referências
```

## Pré-requisitos

| Ferramenta | Versão mínima |
|---|---|
| Docker + Docker Compose | 24 |
| Node.js | 22 |
| Python | 3.12 |

## Subir o ambiente completo

```bash
cp .env.example .env        # preencha as variáveis obrigatórias
docker compose up --build   # sobe PostgreSQL, Redis, backend e frontend
```

Após o build:

- Frontend: <http://localhost:4200>
- API: <http://localhost:8000>
- Health check: `GET http://localhost:8000/health` → `200 {"status":"ok"}`

## Desenvolvimento local (sem Docker)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run start               # abre em http://localhost:4200
```

## Testes e qualidade

```bash
# Backend
cd backend
ruff check .
mypy .
pytest

# Frontend
cd frontend
npx eslint .
npx tsc --noEmit
ng test --watch=false
```

O CI (ver `.github/workflows/`) executa todos os checks acima em cada push e bloqueia merges com falha.

## Documentação

- [PRD](docs/PRD_Agente_Traducao_Manga_Japones.md) — visão de produto, fases e roadmap
- [Especificação do Frontend](docs/FRONTEND_Especificacao.md) — wireframes, rotas e cards de entrega
