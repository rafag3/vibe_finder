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

## 4. Preencher o cache antes de mostrar pra alguém

Esse é o passo que faz diferença de verdade e o motivo do
`backend/data/warm_cache.py` existir.

O free tier do Render tem **filesystem efêmero**: o `tracks.db` volta ao estado do commit
a cada restart, redeploy ou spin-down. Como o cache de vídeo mora nesse arquivo, sem
pré-preencher ele nasce vazio toda vez — e cada play numa faixa não cacheada dispara um
`search.list`, que custa **100 das 10.000 unidades diárias** de cota. São ~100 plays por
dia antes de tudo cair no vídeo mock.

Rode localmente, com a chave na `.env`, e **commite o `.db` resultante**:

```bash
cd backend
python -m data.warm_cache --limit 95              # dia 1
python -m data.warm_cache --limit 95 --skip 95    # dia 2 (são 127 faixas)
git add data/tracks.db && git commit -m "cache de video pre-populado" && git push
```

Com o cache completo no commit, a produção só **lê** o banco — o filesystem efêmero deixa
de importar na prática, e a cota diária fica intacta para faixas novas.

---

## Limitações conhecidas do free tier

| Limitação | Efeito | Mitigação |
|---|---|---|
| Render dorme após 15 min ocioso | Primeira geração após ociosidade leva ~1 min | Aceitar, ou $7/mês para always-on |
| Filesystem efêmero | Cache e histórico somem no restart | `warm_cache.py` (passo 4) |
| Cota YouTube 10k/dia | ~100 buscas novas/dia | Cache pré-populado |
| CORS fixo em `FRONTEND_ORIGIN` | Preview deploys da Vercel (URLs variáveis) são bloqueados | Adicionar a URL do preview ao `FRONTEND_ORIGIN`, ou testar só em produção |

Manter o serviço acordado com um ping externo consome as 750 h/mês inteiras (744 h em um
mês cheio) em um único serviço, e o Render não trata isso como uso suportado.

---

## Por que não colocar tudo na Vercel

O backend escreve no SQLite em três pontos: cache de vídeo (`youtube/client.py`), cache de
capa/preview (`cover_art/client.py`) e histórico (`generated_playlists` em `app.py`). O
runtime serverless da Vercel tem **filesystem somente leitura** fora de `/tmp`, e `/tmp`
não sobrevive entre invocações. As escritas falhariam ou seriam descartadas silenciosamente
a cada request, o que na prática significa **zero cache e queima total da cota**.

Quando a arquitetura atual incomodar, o próximo passo correto não é mudar de host: é mover
as três escritas para um Postgres gerenciado (Supabase free, por exemplo). São 127 linhas e
3 tabelas — a migração é pequena. Aí o cache passa a persistir de verdade, o histórico para
de sumir, e o backend fica livre para rodar em qualquer plataforma, serverless inclusive.
