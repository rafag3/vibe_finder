# Deploy — Vibe Finder

Arquitetura em produção: **frontend estático na Vercel** + **backend Flask no Render**.
São duas plataformas porque o backend não é estático nem stateless — ver "Por que não
tudo na Vercel" no fim.

---

## 0. Antes de qualquer coisa (segurança)

1. **Rotacione a `YOUTUBE_API_KEY`.** A chave antiga estava em `backend/.env` dentro do
   zip. Considere-a comprometida: gere uma nova no Google Cloud Console e apague a antiga.
2. Na chave nova, aplique **restrição de API**: apenas *YouTube Data API v3*. Não dá pra
   restringir por IP (o Render não garante IP fixo no free), então a restrição de API é a
   única barreira — sem ela, uma chave vazada dá acesso a tudo do projeto GCP.
3. O `.env` **não** vai para o repositório. Já está no `.gitignore`; use `.env.example`
   como referência e coloque os valores reais direto no painel do Render.

---

## 1. Subir para o GitHub

```bash
cd vibe_finder
git init
git add .
git commit -m "vibe finder: app inicial + configs de deploy"
git branch -M main
git remote add origin git@github.com:rafag3/vibe-finder.git
git push -u origin main
```

Confira antes do push que `git status` **não** lista `backend/.env`, `backend/venv/` nem
`frontend/node_modules/`.

---

## 2. Backend no Render

1. Dashboard → **New → Web Service** → conecte o repositório.
2. O `render.yaml` na raiz já define runtime, `rootDir`, build e start command. Se preferir
   configurar na mão:
   - Root Directory: `backend`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 60`
   - Health Check Path: `/health`
3. Environment → adicione:
   - `YOUTUBE_API_KEY` = a chave nova
   - `FRONTEND_ORIGIN` = `https://<seu-projeto>.vercel.app` (preencha depois do passo 3)
   - `SUPABASE_URL` e `SUPABASE_KEY` = do projeto Supabase (ver seção "Cache
     persistente" abaixo) — sem eles o cache de vídeo/capa não sobrevive a
     um restart, e cada restart volta a queimar cota do YouTube do zero.
4. Deploy. Valide: `curl https://<seu-servico>.onrender.com/health` → `{"status":"ok"}`

**1 worker é intencional.** O SQLite não aguenta escrita concorrente de múltiplos
processos (`database is locked`). As threads cobrem a carga, que é I/O-bound (chamadas
HTTP ao YouTube/iTunes).

---

## 3. Frontend na Vercel

1. **Add New → Project** → mesmo repositório.
2. **Root Directory: `frontend`** (crítico — sem isso a Vercel tenta buildar a raiz e falha).
3. Framework Preset: Vite. Build `npm run build`, output `dist` (auto-detectado).
4. Environment Variables → `VITE_API_URL` = `https://<seu-servico>.onrender.com`
   *(sem barra no fim)*.
5. Deploy → volte ao Render e preencha `FRONTEND_ORIGIN` com a URL da Vercel.

`VITE_API_URL` é embutida no bundle em build time, não lida em runtime. Trocar a variável
exige **redeploy** do frontend, não basta salvar.

---

## 4. Cache persistente (Supabase) + preencher antes de mostrar pra alguém

O free tier do Render tem **filesystem efêmero**: qualquer coisa escrita em runtime
(inclusive um SQLite local) some a cada restart, redeploy ou spin-down. Por isso o
cache de vídeo do YouTube, o cache de capa/preview do iTunes e o histórico de
playlists moram no **Supabase** (Postgres gerenciado, free tier), não no
`tracks.db` — o `tracks.db` local ficou só como catálogo estático de faixas
(comitado no git, nunca escrito em runtime).

1. Crie um projeto em [supabase.com](https://supabase.com) (free tier).
2. Rode as migrations que criam as 3 tabelas (`video_cache`, `cover_cache`,
   `generated_playlists`) e as RLS policies — ver `backend/storage/supabase_client.py`
   pro schema esperado por cada tabela.
3. Pegue a URL do projeto e a chave `anon` (Project Settings → API) e configure
   `SUPABASE_URL`/`SUPABASE_KEY` no Render (passo 2) e no `.env` local.

Sem cota do YouTube envolvida, isso já resolve o problema pra sempre — o cache
persiste entre deploys, sem precisar commitar nada. Ainda vale rodar o warm-up
antes de divulgar o link, porque cada faixa sem cache custa **100 das 10.000
unidades diárias** de cota (`search.list`):

```bash
cd backend
python -m data.warm_cache --limit 95              # respeita a cota do dia
python -m data.warm_cache --limit 95 --skip 95    # dia seguinte, se sobrar faixa
```

Não precisa commitar nada depois — o cache já está no Supabase, não no `.db` local.

---

## Limitações conhecidas do free tier

| Limitação | Efeito | Mitigação |
|---|---|---|
| Render dorme após 15 min ocioso | Primeira geração após ociosidade leva ~1 min | Aceitar, ou $7/mês para always-on |
| Cota YouTube 10k/dia | ~100 buscas novas/dia | Cache no Supabase + `warm_cache.py` (passo 4) |
| CORS fixo em `FRONTEND_ORIGIN` | Preview deploys da Vercel (URLs variáveis) são bloqueados | Adicionar a URL do preview ao `FRONTEND_ORIGIN`, ou testar só em produção |

Manter o serviço acordado com um ping externo consome as 750 h/mês inteiras (744 h em um
mês cheio) em um único serviço, e o Render não trata isso como uso suportado.

---

## Por que não colocar tudo na Vercel

O backend tem três pontos de escrita: cache de vídeo (`youtube/client.py`), cache de
capa/preview (`cover_art/client.py`) e histórico (`generated_playlists` em `app.py`) — hoje
todos no Supabase, não mais no SQLite local (ver seção "Cache persistente" acima). O runtime
serverless da Vercel tem **filesystem somente leitura** fora de `/tmp`, e `/tmp` não sobrevive
entre invocações — isso inviabilizaria escritas locais, mas não afeta escritas num Postgres
gerenciado externo como o Supabase.

Na prática isso significa que o backend já não depende de disco gravável pra funcionar
corretamente — poderia rodar em qualquer plataforma, serverless inclusive. A escolha por
Render continua sendo sobre simplicidade (processo Flask de longa duração, sem reescrever
pra functions) e não mais uma exigência técnica do cache.
