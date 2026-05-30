# Job Analyzer

Backend FastAPI para o sistema RH & Jobs, com frontend HTML/CSS/JS hospedado separadamente em:

```text
https://rhejobs.com.br/app
```

## Estrutura

```text
job-analyzer/
├── backend/
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   └── services/
├── frontend/
├── data/
├── uploads/
├── logs/
├── requirements.txt
├── start.sh
├── render.yaml
└── .env.example
```

## Rodar localmente

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

No Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Teste:

```text
http://localhost:8000/
http://localhost:8000/docs
```

O endpoint raiz deve retornar:

```json
{
  "status": "online",
  "service": "job-analyzer"
}
```

## Endpoints principais

- `GET /` healthcheck do Render
- `GET /docs` documentação automática FastAPI
- `POST /login` autenticação
- `GET /me` usuário autenticado
- `POST /analyze` análise de currículo
- `POST /analisar` alias legado da análise
- `GET /cargos` lista cargos
- `POST /cargo/buscar` busca cargo

## Variáveis de ambiente

Configure no Render:

```text
API_URL=https://SEU-BACKEND-RENDER.onrender.com
DATABASE_URL=sqlite:///data/database.db
APP_BASE_PATH=/app
CORS_ORIGINS=*
COOKIE_SAMESITE=none
COOKIE_SECURE=true
AUTH_REQUIRED=true
```

Observação: o código usa `sqlite:///data/database.db`, caminho relativo e compatível com Linux/Render.

## Deploy no Render

1. Suba este projeto para um repositório GitHub.
2. No Render, clique em `New +` e selecione `Web Service`.
3. Conecte o repositório do GitHub.
4. Configure:

```text
Runtime: Python
Build Command: pip install -r requirements.txt
Start Command: bash start.sh
```

5. Adicione as variáveis de ambiente listadas acima.
6. Faça o deploy.
7. Abra:

```text
https://SEU-BACKEND-RENDER.onrender.com/
https://SEU-BACKEND-RENDER.onrender.com/docs
```

## Deploy via render.yaml

O arquivo `render.yaml` já contém:

```yaml
services:
  - type: web
    name: job-analyzer
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: bash start.sh
```

## Integração com Hostinger

No frontend hospedado em `https://rhejobs.com.br/app`, ajuste:

```js
window.RHJOB_API_URL = "https://SEU-BACKEND-RENDER.onrender.com";
```

em `frontend/config.js`, substituindo pelo domínio real gerado pelo Render.

## Subir no GitHub

```bash
git init
git add .
git commit -m "Prepare Render deploy"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/job-analyzer.git
git push -u origin main
```
