# Vibe Finder

Gerador de playlist por mood/vibe. Backend Flask (API pura) + frontend React/Vite.

```
playlist-mood-project/
├── backend/    Flask API (matching engine, SQLite p/ catálogo, Supabase p/ cache)
└── frontend/   React + Vite + Framer Motion
```

## Backend (Flask API)

**Windows (PowerShell):**
```powershell
cd backend
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```
Se o PowerShell bloquear o Activate.ps1 (erro de execution policy), roda antes:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

**Linux/Mac:**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
```

Cria um `.env` dentro de `backend/` com (veja `.env.example`):
```
YOUTUBE_API_KEY=sua_chave_aqui
FRONTEND_ORIGIN=http://localhost:5173
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_KEY=sua_chave_anon
```
`SUPABASE_URL`/`SUPABASE_KEY` são opcionais em dev: sem elas o app funciona
normalmente, só não persiste o cache de vídeo/capa entre reinícios (ver
`DEPLOY.md` pra por que isso importa em produção).

Roda o dataset (se ainda não tiver `data/tracks.db` populado):
```
python data/load_dataset.py
```
Sobe a API (com a venv ativada):
```
python app.py
```
Vai subir em `http://localhost:5000`.

## Frontend (React + Vite)
```
cd frontend
npm install
npm run dev
```
Vai subir em `http://localhost:5173`.

Se mudar a porta/URL do backend, cria um `.env` dentro de `frontend/`:
```
VITE_API_URL=http://localhost:5000
```

## Build de produção do front
```
cd frontend
npm run build
```
Gera `frontend/dist/` — arquivos estáticos.
